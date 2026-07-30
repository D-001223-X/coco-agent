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
    """A single retrieved chunk with RRF-fused score."""

    chunk_id: str
    content: str
    score: float
    section: str = ""

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

    def __init__(self) -> None:
        self._settings = get_settings()
        self._faiss_index: faiss.Index | None = None
        self._chunks: list[dict] | None = None

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
        top_k: int = 3,
        threshold: float = 0.3,
        trace_id: str | None = None,
    ) -> list[RetrievedChunk]:
        """Hybrid search: FAISS + FTS5 → RRF → threshold → top_k."""
        trace_id = trace_id or uuid.uuid4().hex
        start_ts = time.perf_counter()
        status = "ok"

        try:
            results = await self._hybrid_search(query, top_k, threshold)
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

    # ── Internal: hybrid search ────────────────────────────
    async def _hybrid_search(
        self,
        query: str,
        top_k: int,
        threshold: float,
    ) -> list[RetrievedChunk]:
        fetch_k = 20

        faiss_task = asyncio.create_task(self._faiss_search(query, fetch_k, threshold))
        fts5_task = asyncio.create_task(self._fts5_search(query, fetch_k))

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
            )
            for cid, content, score, section in filtered
        ]

    # ── FAISS vector search (thread pool) ──────────────────
    async def _faiss_search(
        self, query: str, k: int, threshold: float = 0.0
    ) -> list[tuple[str, str, float, str]]:
        await asyncio.to_thread(self._load_index)

        if self._faiss_index is None or self._chunks is None:
            return []

        def _search() -> list[tuple[str, str, float, str]]:
            vec = text_to_vector(query).reshape(1, -1)
            faiss.normalize_L2(vec)

            k_actual = min(k, self._faiss_index.ntotal)
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
        self, query: str, k: int
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

        # If FTS5 returns no results (common for Chinese text with unicode61),
        # fall back to Python-based keyword matching on all chunks.
        if not rows and self._chunks:
            rows = self._fallback_keyword_search(query, tokens, k)

        return [
            (str(row[0]), row[1], float(abs(row[2])), "")
            for row in rows
        ]

    # ── Fallback keyword search (for Chinese text) ──────────
    def _fallback_keyword_search(
        self, query: str, tokens: list[str], k: int
    ) -> list[tuple[str, str, float]]:
        """Score chunks by keyword match when FTS5 can't handle the text."""
        if not self._chunks:
            return []

        scored: list[tuple[str, str, float]] = []
        for chunk in self._chunks:
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
    @staticmethod
    def _rrf_fuse(
        faiss_results: list[tuple[str, str, float, str]],
        fts5_results: list[tuple[str, str, float, str]],
    ) -> list[tuple[str, str, float, str]]:
        scores: dict[str, float] = {}
        meta: dict[str, tuple[str, str]] = {}

        for rank, (cid, content, _, section) in enumerate(faiss_results):
            rrf = 1.0 / (_RRF_K + rank + 1)
            scores[cid] = scores.get(cid, 0.0) + rrf
            if cid not in meta:
                meta[cid] = (content, section)

        for rank, (cid, content, _, section) in enumerate(fts5_results):
            rrf = 1.0 / (_RRF_K + rank + 1)
            scores[cid] = scores.get(cid, 0.0) + rrf
            if cid not in meta:
                meta[cid] = (content, section)

        fused = [
            (cid, meta[cid][0], score, meta[cid][1])
            for cid, score in scores.items()
        ]
        fused.sort(key=lambda x: x[2], reverse=True)
        return fused[:10]
