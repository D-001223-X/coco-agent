"""Build FAISS index, chunks metadata, and populate FTS5 from the knowledge base.

Run:  uv run --no-sync python -m scripts.build_index

This script is idempotent — safe to re-run.
Uses pure-numpy character n-gram hashing for vectorisation (no sklearn/scipy).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path

import faiss
import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import get_settings
from app.models import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base"

VECTOR_DIM = 256


# ── Markdown chunker ──────────────────────────────────────
# FAQ marker patterns — supports "Q:/A:" style and "问：/答：" style.
_QA_START_RE = re.compile(
    r"^\s*(?P<marker>Q|A|问|答)\s*[:：]\s*",
    re.IGNORECASE,
)

# Question words used to validate a candidate Q (Chinese + English).
_QUESTION_WORDS = (
    "吗", "呢", "么", "什么", "怎么", "怎样", "如何", "为啥", "为什么",
    "哪", "谁", "何时", "多少", "有没有", "能否", "是不是", "可否", "怎么办",
    "what", "how", "why", "when", "where", "who", "which", "can", "do", "is", "are",
)


def is_faq_block(content: str) -> bool:
    """Detect whether *content* looks like a FAQ block.

    Heuristics (any strong signal wins):
      1. Structured Q:/A: / 问：/ 答： markers appear ≥ 2 times.
      2. Question-sentence density ≥ 0.25 among non-empty lines.
      3. Alternating Q-A-Q-A pattern (consecutive Q&A).
    """
    if not content or not content.strip():
        return False

    lines = [ln.strip() for ln in content.split("\n") if ln.strip()]
    if len(lines) < 3:
        return False

    # 1) structured markers
    marker_count = sum(1 for ln in lines if _QA_START_RE.match(ln))
    if marker_count >= 2:
        return True

    # 2) question-sentence density
    q_lines = sum(1 for ln in lines if _ends_with_question(ln))
    if q_lines / len(lines) >= 0.25 and q_lines >= 2:
        return True

    # 3) alternating Q-A pattern (Q, then A within next 2 lines, repeated)
    alt_pairs = 0
    i = 0
    while i < len(lines) - 1:
        if _looks_like_question(lines[i]):
            # an answer must follow within the next 2 lines
            for j in range(i + 1, min(i + 3, len(lines))):
                if _looks_like_answer(lines[j]):
                    alt_pairs += 1
                    i = j + 1
                    break
            else:
                i += 1
        else:
            i += 1
    return alt_pairs >= 2


def _ends_with_question(line: str) -> bool:
    """True if a line ends with a question mark or contains a question word."""
    stripped = line.strip()
    if stripped.endswith(("?", "？")):
        return True
    # strip trailing punctuation but NOT question marks (already checked above)
    stripped = stripped.rstrip("。.!！ ")
    if stripped.endswith(("?", "？")):
        return True
    low = stripped.lower()
    return any(w in low for w in _QUESTION_WORDS)


def _looks_like_question(line: str) -> bool:
    return _ends_with_question(line) or bool(_QA_START_RE.match(line))


def _looks_like_answer(line: str) -> bool:
    return bool(re.match(r"^\s*(?:A\s*[:：]|答\s*[:：])", line, re.IGNORECASE))


def is_valid_qa_pair(q: str, a: str) -> bool:
    """Validate a candidate Q/A pair.

    Rules: Q and A must both be non-empty, Q must contain a question word or
    end with a question mark, and Q/A must not be the same text.
    """
    q = q.strip()
    a = a.strip()
    if not q or not a:
        return False
    if not _ends_with_question(q) and not _looks_like_question(q):
        return False
    if q == a:
        return False
    return True


def split_faq_pairs(content: str) -> list[tuple[str, str]] | None:
    """Split a FAQ block into (question, answer) pairs.

    Strategy:
      1. Prefer Q:/A: / 问：/ 答： markers.
      2. Fall back to consecutive question-sentence splitting.
      3. Return None (→ keep block intact) when:
         - fewer than 2 valid pairs produced
         - markers exist but Q/A counts mismatch badly (unmatched Q with no A)

    Returns ``None`` to signal "not splittable — keep original block".
    """
    lines = [ln.strip() for ln in content.split("\n") if ln.strip()]

    # ── Strategy 1: marker-based split ────────────────────
    pairs: list[tuple[str, str]] = []
    cur_q: str | None = None
    cur_a_parts: list[str] = []
    saw_marker = False

    for ln in lines:
        m = _QA_START_RE.match(ln)
        if m:
            marker = m.group("marker").upper()  # Q / A / 问 / 答
            rest = ln[m.end():].strip()
            if marker in ("Q", "问"):
                # flush previous pair
                if cur_q is not None:
                    a_text = " ".join(cur_a_parts).strip()
                    if is_valid_qa_pair(cur_q, a_text):
                        pairs.append((cur_q, a_text))
                    # Q without A → ignored (per spec)
                cur_q = rest
                cur_a_parts = []
            else:  # A / 答
                saw_marker = True
                cur_a_parts.append(rest)
        else:
            # plain line: append to the current answer accumulation
            cur_a_parts.append(ln)

    # flush last pair
    if cur_q is not None:
        a_text = " ".join(cur_a_parts).strip()
        if is_valid_qa_pair(cur_q, a_text):
            pairs.append((cur_q, a_text))

    if saw_marker and len(pairs) >= 2:
        return pairs

    # ── Strategy 2: question-density split (marker-free) ──
    if not saw_marker:
        pairs2: list[tuple[str, str]] = []
        i = 0
        while i < len(lines):
            if _looks_like_question(lines[i]):
                q = lines[i]
                a_parts: list[str] = []
                i += 1
                while i < len(lines) and not _looks_like_question(lines[i]):
                    a_parts.append(lines[i])
                    i += 1
                a_text = " ".join(a_parts).strip()
                if is_valid_qa_pair(q, a_text):
                    pairs2.append((q, a_text))
            else:
                i += 1
        if len(pairs2) >= 2:
            return pairs2

    return None


def _split_section_chunks(
    section: str, content: str, start_id: int, id_prefix: str = ""
) -> list[dict]:
    """Split one section block; FAQ blocks get fine-grained QA chunks."""

    def _cid(n: int) -> str:
        return f"{id_prefix}:{n}" if id_prefix else str(n)

    faq_pairs = split_faq_pairs(content)
    if faq_pairs is None:
        # normal block — keep as one chunk
        return [{
            "chunk_id": _cid(start_id),
            "content": content,
            "section": section,
        }]

    chunks: list[dict] = []
    # keep the section heading line as a short "index" chunk so the section
    # title still retrievable, then one chunk per Q&A pair
    heading_line = next(
        (ln for ln in content.split("\n") if ln.strip().startswith("## ")),
        "",
    ).strip()
    if heading_line:
        chunks.append({
            "chunk_id": _cid(start_id + len(chunks)),
            "content": heading_line,
            "section": section,
        })

    for q, a in faq_pairs:
        chunks.append({
            "chunk_id": _cid(start_id + len(chunks)),
            "content": f"Q: {q}\nA: {a}",
            "section": section,
        })
    return chunks


def chunk_markdown(md_text: str, id_prefix: str = "") -> list[dict]:
    """Split markdown by ## headings, then fine-split FAQ blocks.

    Layer 1: split by ``## `` headings into section blocks.
    Layer 2: detect FAQ blocks via ``is_faq_block``.
    Layer 3: fine-split FAQ blocks into (Q, A) chunks via ``split_faq_pairs``.
    Non-FAQ blocks stay as-is.

    Parameters
    ----------
    id_prefix : str
        文件名前缀（如 "cefr_standards.md"），用于生成**全局唯一** chunk_id。
        多文件合并建索引时若不传前缀，各文件 chunk_id 会从 0 重复，
        导致 FAISS/FTS5 结果按 chunk_id 融合时互相覆盖（检索污染）。
    """
    lines = md_text.split("\n")
    chunks: list[dict] = []
    section_blocks: list[tuple[str, str]] = []  # (heading, body_with_heading)
    current_heading = ""
    current_lines: list[str] = []

    def _cid(n: int) -> str:
        return f"{id_prefix}:{n}" if id_prefix else str(n)

    for line in lines:
        if line.startswith("## "):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    section_blocks.append((current_heading, content))
            current_heading = line.lstrip("# ").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            section_blocks.append((current_heading, content))

    for heading, body in section_blocks:
        # Layer 2: FAQ detection (skip the heading line itself)
        body_no_heading = "\n".join(
            ln for ln in body.split("\n") if not ln.strip().startswith("## ")
        )
        if is_faq_block(body_no_heading):
            chunks.extend(_split_section_chunks(heading, body, len(chunks), id_prefix))
        else:
            chunks.append({
                "chunk_id": _cid(len(chunks)),
                "content": body,
                "section": heading,
            })
    return chunks


# ── Pure-numpy n-gram hashing vectoriser ──────────────────
def _ngram_hash(text: str, n: int) -> list[int]:
    """Extract character n-grams and return their bucket hashes."""
    buckets = []
    for i in range(len(text) - n + 1):
        gram = text[i : i + n]
        h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
        buckets.append(h % VECTOR_DIM)
    return buckets


def text_to_vector(text: str, dim: int = VECTOR_DIM) -> np.ndarray:
    """Convert text to a dense vector using character n-gram hashing.

    For each n in {2, 3, 4}, extract n-grams, hash to bucket, count
    occurrences.  The result is a sparse-count vector of length *dim*.
    """
    vec = np.zeros(dim, dtype=np.float32)
    for n in (2, 3, 4):
        for bucket in _ngram_hash(text, n):
            vec[bucket] += 1.0
    return vec


def build_vectors(chunks: list[dict], dim: int = VECTOR_DIM) -> np.ndarray:
    """Build a (N, dim) matrix of n-gram hash vectors."""
    vectors = np.stack([text_to_vector(c["content"], dim) for c in chunks])
    faiss.normalize_L2(vectors)
    return vectors


def build_faiss_index(chunks: list[dict], dim: int = VECTOR_DIM):
    """Build a FAISS IndexFlatIP from chunk text."""
    vectors = build_vectors(chunks, dim)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index, vectors


# ── FTS5 populator ────────────────────────────────────────
async def populate_fts5(chunks: list[dict], db_url: str) -> None:
    """Insert chunk content into the FTS5 virtual table.

    Schema: (title, content, chunk_id) — ``chunk_id`` is UNINDEXED because
    it is only used as a foreign key back to the chunks metadata.
    The virtual table is dropped and recreated so schema changes are applied
    idempotently on every rebuild.

    **SQLite only**: MySQL/CloudBase 云数据库无 FTS5，本函数直接跳过
    （检索走 FAISS 向量 + Python 关键词匹配）。
    """
    if not db_url.startswith("sqlite"):
        print("INFO  populate_fts5 skipped (non-SQLite backend: FTS5 unavailable)")
        return

    engine = create_async_engine(db_url, echo=False)

    async with engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Drop and recreate to guarantee the latest schema is in place.
        await conn.execute(text("DROP TABLE IF EXISTS knowledge_fts;"))
        await conn.execute(text("""
            CREATE VIRTUAL TABLE knowledge_fts
            USING fts5(
                title,
                content,
                chunk_id      UNINDEXED,
                tokenize = 'unicode61'
            );
        """))
        await conn.execute(text("DELETE FROM knowledge_fts;"))
        for chunk in chunks:
            await conn.execute(
                text(
                    "INSERT INTO knowledge_fts (title, content, chunk_id) "
                    "VALUES (:title, :content, :chunk_id);"
                ),
                {
                    "title": chunk.get("section", ""),
                    "content": chunk["content"],
                    "chunk_id": chunk["chunk_id"],
                },
            )
        await conn.commit()

    await engine.dispose()
    logger.info("FTS5 populated with %d chunks.", len(chunks))


# ── Main ──────────────────────────────────────────────────
async def main() -> None:
    """Build and save all retrieval artifacts."""
    s = get_settings()

    if not KB_DIR.exists():
        raise FileNotFoundError(f"知识库目录不存在: {KB_DIR}")

    md_files = sorted(KB_DIR.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(
            f"知识库目录为空，请先上传 .md 文件: {KB_DIR}"
        )

    # Merge chunks from all .md files; each chunk keeps a source file reference
    # 传文件名前缀保证 chunk_id 全局唯一（多文件不重复）
    chunks: list[dict] = []
    for md_file in md_files:
        md_text = md_file.read_text(encoding="utf-8")
        file_chunks = chunk_markdown(md_text, id_prefix=md_file.name)
        for c in file_chunks:
            c["source_file"] = md_file.name
        chunks.extend(file_chunks)
        logger.info("Read %s: %d chars → %d chunks", md_file.name, len(md_text), len(file_chunks))

    logger.info("Total chunks across %d files: %d", len(md_files), len(chunks))

    index, _ = build_faiss_index(chunks)
    faiss_path = Path(s.faiss_index_path).resolve()
    faiss.write_index(index, str(faiss_path))
    logger.info("FAISS index saved to %s", faiss_path)

    chunks_path = Path(s.chunks_meta_path).resolve()
    chunks_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Chunks metadata saved to %s (%d entries)", chunks_path, len(chunks))

    await populate_fts5(chunks, s.effective_database_url)
    logger.info("All artifacts built successfully.")


if __name__ == "__main__":
    asyncio.run(main())
