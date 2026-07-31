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
def chunk_markdown(md_text: str) -> list[dict]:
    """Split markdown by ## headings into chunks."""
    lines = md_text.split("\n")
    chunks: list[dict] = []
    current_heading = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    chunks.append({
                        "chunk_id": str(len(chunks)),
                        "content": content,
                        "section": current_heading,
                    })
            current_heading = line.lstrip("# ").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            chunks.append({
                "chunk_id": str(len(chunks)),
                "content": content,
                "section": current_heading,
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
    """
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
    chunks: list[dict] = []
    for md_file in md_files:
        md_text = md_file.read_text(encoding="utf-8")
        file_chunks = chunk_markdown(md_text)
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

    await populate_fts5(chunks, s.database_url)
    logger.info("All artifacts built successfully.")


if __name__ == "__main__":
    asyncio.run(main())
