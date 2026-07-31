"""Hybrid retrieval service: FAISS semantic search + FTS5 BM25 + RRF fusion.

Architecture:
  • FAISS vector search (top-20) runs in a thread pool — never blocks the
    async event loop.
  • FTS5 BM25 keyword search (top-20) runs via async SQLAlchemy.
  • Results are fused with Reciprocal Rank Fusion (RRF, k=60).
  • Deduplication by chunk_id, threshold filtering, top-k truncation.
  • Every call is logged via ``log_node`` (fire-and-forget).

Uses pure-numpy character n-gram hashing for vectorisation (no sklearn/scipy).
No synchronous I/O on the event loop. No hardcoded paths.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sqlalchemy import text

from app.config import get_settings
from app.database import get_session_factory
from app.utils.logger import log_node

logger = logging.getLogger(__name__)

_RRF_K = 60
VECTOR_DIM = 256


# ── Result dataclass ─────────────────────────────────────
@dataclass
class RetrievedChunk:
    """A single retrieved chunk with RRF-fused score and raw scores."""

    chunk_id: str
    content: str
    score: float
    section: str = ""
    faiss_score: float | None = None
    bm25_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── Pure-numpy n-gram hashing (mirrors build_index.py) ───
def _ngram_hash(text: str, n: int, dim: int = VECTOR_DIM) -> list[int]:
    buckets = []
    for i in range(len(text) - n + 1):
        gram = text[i : i + n]
        h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
        buckets.append(h % dim)
    return buckets


def text_to_vector(text: str, dim: int = VECTOR_DIM) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    for n in (2, 3, 4):
        for bucket in _ngram_hash(text, n, dim):
            vec[bucket] += 1.0
    return vec


class RetrievalService:
    """Hybrid retrieval combining FAISS and FTS5 with RRF fusion."""

    # Admin-tunable parameter defaults (see ParamService / admin API)
    DEFAULT_PARAMS: dict[str, float | int] = {
        "faiss_top_k": 20,
        "fts5_top_k": 20,
        "threshold": 0.3,
        "rrf_k": 60,
        "final_top_k": 3,
    }

    def __init__(self) -> None:
        self._settings = get_settings()
        self._faiss_index: faiss.Index | None = None
        self._chunks: list[dict] | None = None
        self._params: dict[str, float | int] = dict(self.DEFAULT_PARAMS)

    # ── Admin parameter management ─────────────────────────
    def get_params(self) -> dict:
        return dict(self._params)

    def update_params(self, params: dict) -> dict:
        for key, value in params.items():
            if key in self.DEFAULT_PARAMS and value is not None:
                self._params[key] = value
        logger.info("[retrieval] params updated: %s", self._params)
        return self.get_params()

    def reset_params(self) -> dict:
        self._params = dict(self.DEFAULT_PARAMS)
        logger.info("[retrieval] params reset to defaults")
        return self.get_params()

    # ── Lazy loader (called in thread pool) ───────────────
    def _load_index(self) -> None:
        """Load FAISS index + chunks metadata.  Runs in a thread."""
        if self._faiss_index is not None:
            return

        s = self._settings
        faiss_path = Path(s.faiss_index_path)
        chunks_path = Path(s.chunks_meta_path)

        if not faiss_path.exists():
            raise FileNotFoundError(f"FAISS index not found: {faiss_path}")
        if not chunks_path.exists():
            raise FileNotFoundError(f"Chunks metadata not found: {chunks_path}")

        self._faiss_index = faiss.read_index(str(faiss_path))
        self._chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    # ── Public API ─────────────────────────────────────────
    async def search(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        trace_id: str | None = None,
        sections: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Hybrid search: FAISS + FTS5 → RRF → threshold → top_k.

        When *top_k* / *threshold* are omitted, the current admin-tunable
        params (``final_top_k`` / ``threshold``) are used — so tuning via
        the admin API takes effect immediately.

        *sections*: optional list of section names to restrict retrieval to.
        When provided, chunks whose ``section`` doesn't match are excluded
        (intent-driven section-constrained retrieval).
        """
        trace_id = trace_id or uuid.uuid4().hex
        start_ts = time.perf_counter()
        status = "ok"

        # Use tunable params when not explicitly overridden by caller
        if top_k is None:
            top_k = int(self._params["final_top_k"])
        if threshold is None:
            threshold = float(self._params["threshold"])

        try:
            results = await self._hybrid_search(query, top_k, threshold, sections)
            # 章节限定检索无结果时，回退全库检索（兜底，防止误拒）
            if not results and sections:
                logger.info(
                    "[retrieval] section-filtered (%s) empty → fallback to full search",
                    sections,
                )
                results = await self._hybrid_search(query, top_k, threshold, None)
        except Exception as exc:
            import traceback
            logger.error(
                "[retrieval] FAILED query=%r error=%s\n%s",
                query, exc, traceback.format_exc(),
            )
            results = []
            status = "error"

        logger.info(
            "[retrieval] query=%r top_k=%d threshold=%.2f results=%d first3=%s",
            query, top_k, threshold, len(results),
            [(r.chunk_id, r.content[:40], round(r.score, 3)) for r in results[:3]],
        )

        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        output_summary = {
            "count": len(results),
            "top_scores": [round(r.score, 4) for r in results[:5]],
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "rrf_score": round(r.score, 4),
                    "faiss_score": round(r.faiss_score, 4) if r.faiss_score is not None else None,
                    "bm25_score": round(r.bm25_score, 4) if r.bm25_score is not None else None,
                    "section": r.section,
                    "content_preview": r.content[:100],
                }
                for r in results
            ],
        }
        try:
            log_node(
                trace_id=trace_id,
                node="retrieval",
                input_data={"query": query, "top_k": top_k, "threshold": threshold},
                output_data=output_summary,
                duration_ms=duration_ms,
                service="FAISS+FTS5+RRF",
                status=status,
            )
        except Exception as log_exc:
            logger.warning("log_node scheduling failed: %s", log_exc)

        return results

    # ── Section matching (fuzzy, tolerant of LLM title drift) ─
    @staticmethod
    def _section_matches(section: str, targets: list[str]) -> bool:
        """Loose match: strip numbering prefix, then substring/keyword overlap.

        Handles cases where the LLM returns e.g. "五、会员与付费方案" while the
        real section title is "五、账号与付费方案".
        """
        import re as _re

        def _clean(text: str) -> str:
            # strip leading numbering like "五、" / "5." / "5、"
            cleaned = _re.sub(r"^[一二三四五六七八九十\d]+\s*[、.．]\s*", "", text.strip())
            return cleaned

        if not targets:
            return True

        section = section.strip()
        if not section:
            # 空章节（如文档头部）不参与章节限定匹配
            return False

        section_clean = _clean(section)
        for target in targets:
            target_clean = _clean(target)
            if not target_clean:
                continue
            # exact or substring in either direction
            if (
                target_clean in section_clean
                or section_clean in target_clean
                or target_clean in section
                or section in target_clean
            ):
                return True
        # keyword overlap: any 2-char+ shared token between target and section
        for target in targets:
            target_clean = _clean(target)
            for i in range(len(target_clean) - 1):
                token = target_clean[i : i + 2]
                if len(token) == 2 and token in section_clean:
                    return True
        return False

    # ── Internal: hybrid search ────────────────────────────
    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        threshold: float,
        sections: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        faiss_k = int(self._params["faiss_top_k"])
        fts5_k = int(self._params["fts5_top_k"])

        faiss_task = asyncio.create_task(
            self._faiss_search(query, faiss_k, threshold, sections)
        )
        fts5_task = asyncio.create_task(self._fts5_search(query, fts5_k, sections))

        faiss_results, fts5_results = await asyncio.gather(
            faiss_task, fts5_task, return_exceptions=True
        )

        if isinstance(faiss_results, Exception):
            import traceback
            logger.error(
                "[retrieval] FAISS search error: %s\n%s",
                faiss_results,
                traceback.format_exc(),
            )
            faiss_results = []
        if isinstance(fts5_results, Exception):
            import traceback
            logger.error(
                "[retrieval] FTS5 search error: %s\n%s",
                fts5_results,
                traceback.format_exc(),
            )
            fts5_results = []

        fused = self._rrf_fuse(faiss_results, fts5_results)

        # Take top_k from RRF ranking — do NOT filter by threshold here
        # (RRF scores are tiny by design; threshold applies to raw scores)
        filtered = fused[:top_k]

        return [
            RetrievedChunk(
                chunk_id=cid,
                content=content,
                score=score,
                section=section,
                faiss_score=faiss_score,
                bm25_score=bm25_score,
            )
            for cid, content, score, section, faiss_score, bm25_score in filtered
        ]

    # ── FAISS vector search (thread pool) ──────────────────
    async def _faiss_search(
        self,
        query: str,
        k: int,
        threshold: float = 0.0,
        sections: list[str] | None = None,
    ) -> list[tuple[str, str, float, str]]:
        await asyncio.to_thread(self._load_index)

        if self._faiss_index is None or self._chunks is None:
            return []

        def _search() -> list[tuple[str, str, float, str]]:
            vec = text_to_vector(query).reshape(1, -1)
            faiss.normalize_L2(vec)

            k_actual = min(k * 2, self._faiss_index.ntotal)
            if k_actual == 0:
                return []

            scores, indices = self._faiss_index.search(vec, k_actual)

            results = []
            for idx, score in zip(indices[0], scores[0]):
                if idx < 0:
                    continue
                # Filter by cosine similarity threshold
                if score < threshold:
                    continue
                chunk = self._chunks[idx]
                if not self._section_matches(chunk.get("section", ""), sections):
                    continue
                results.append((
                    chunk["chunk_id"],
                    chunk["content"],
                    float(score),
                    chunk.get("section", ""),
                ))
            return results

        return await asyncio.to_thread(_search)

    # ── FTS5 BM25 search (async SQLAlchemy) ────────────────
    async def _fts5_search(
        self, query: str, k: int, sections: list[str] | None = None
    ) -> list[tuple[str, str, float, str]]:
        session_factory = get_session_factory()

        tokens = [t for t in query.replace("'", "''").split() if t]
        if not tokens:
            tokens = list(query)

        fts_query = " OR ".join(f'"{t}"' for t in tokens)

        sql = text("""
            SELECT chunk_id, content, bm25(knowledge_fts) AS score
            FROM knowledge_fts
            WHERE knowledge_fts MATCH :q
            ORDER BY score
            LIMIT :k
        """)

        async with session_factory() as session:
            result = await session.execute(sql, {"q": fts_query, "k": k})
            rows = result.fetchall()

        logger.debug("[retrieval] FTS5 query=%r tokens=%r rows=%d", query, tokens, len(rows))

        # Section filter for FTS5 rows (fallback keyword path filters too)
        def _match(row) -> bool:
            if not sections:
                return True
            # fetch section via chunks metadata for the given chunk_id
            section = ""
            if self._chunks:
                for c in self._chunks:
                    if c.get("chunk_id") == str(row[0]):
                        section = c.get("section") or ""
                        break
            return self._section_matches(section, sections)

        if sections:
            rows = [r for r in rows if _match(r)]

        # If FTS5 returns no results (common for Chinese text with unicode61),
        # fall back to Python-based keyword matching on all chunks.
        if not rows and self._chunks:
            rows = self._fallback_keyword_search(query, tokens, k, sections)

        return [
            (str(row[0]), row[1], float(abs(row[2])), "")
            for row in rows
        ]

    # ── Fallback keyword search (for Chinese text) ──────────
    def _fallback_keyword_search(
        self, query: str, tokens: list[str], k: int, sections: list[str] | None = None
    ) -> list[tuple[str, str, float]]:
        """Score chunks by keyword match when FTS5 can't handle the text."""
        if not self._chunks:
            return []

        scored: list[tuple[str, str, float]] = []
        for chunk in self._chunks:
            if sections:
                section = (chunk.get("section") or "").strip()
                if not any(s and s in section for s in sections):
                    continue
            content = chunk["content"]
            score = 0.0
            for token in tokens:
                if token and token in content:
                    score += 1.0
            if score > 0:
                scored.append((chunk["chunk_id"], content, score))

        # Sort by score descending, take top_k
        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:k]

    # ── RRF fusion ─────────────────────────────────────────
    def _rrf_fuse(
        self,
        faiss_results: list[tuple[str, str, float, str]],
        fts5_results: list[tuple[str, str, float, str]],
    ) -> list[tuple[str, str, float, str, float | None, float | None]]:
        """RRF fusion; also tracks the raw faiss / bm25 score per chunk."""
        rrf_k = int(self._params["rrf_k"])
        scores: dict[str, float] = {}
        meta: dict[str, tuple[str, str]] = {}
        raw_scores: dict[str, dict[str, float | None]] = {}

        for rank, (cid, content, score, section) in enumerate(faiss_results):
            rrf = 1.0 / (rrf_k + rank + 1)
            scores[cid] = scores.get(cid, 0.0) + rrf
            if cid not in meta:
                meta[cid] = (content, section)
            raw_scores.setdefault(cid, {"faiss": None, "bm25": None})
            raw_scores[cid]["faiss"] = score

        for rank, (cid, content, score, section) in enumerate(fts5_results):
            rrf = 1.0 / (rrf_k + rank + 1)
            scores[cid] = scores.get(cid, 0.0) + rrf
            if cid not in meta:
                meta[cid] = (content, section)
            raw_scores.setdefault(cid, {"faiss": None, "bm25": None})
            raw_scores[cid]["bm25"] = score

        fused = [
            (
                cid,
                meta[cid][0],
                score,
                meta[cid][1],
                raw_scores.get(cid, {}).get("faiss"),
                raw_scores.get(cid, {}).get("bm25"),
            )
            for cid, score in scores.items()
        ]
        fused.sort(key=lambda x: x[2], reverse=True)
        return fused[:10]
