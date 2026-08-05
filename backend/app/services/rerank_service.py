"""Rerank service — calls qwen3-rerank via workspace-specific DashScope domain.

Architecture:
  • Uses ``rerank_base_url`` from config (workspace-specific — NOT dashscope
    public domain).
  • Degrades gracefully: missing API key, timeout, or error → returns original
    documents with score 0.0, never crashes.
  • Every call is logged via ``log_node`` (fire-and-forget, non-blocking).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx

from app.config import get_settings
from app.utils.logger import log_node

logger = logging.getLogger(__name__)


class RerankService:
    """Rerank retrieved documents with qwen3-rerank (DashScope workspace domain).

    All model name, API key and endpoint URL are read from
    ``app.config.Settings`` — nothing is hardcoded.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Public API ─────────────────────────────────────────
    async def rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int = 3,
        trace_id: str | None = None,
        device_id: str | None = None,
    ) -> list[tuple[str, float]]:
        """Rerank *documents* against *query*, return top-*k* results.

        Parameters
        ----------
        query : str
            The search query.
        documents : list[str]
            Documents to rerank.
        top_k : int
            Maximum number of results to return.
        trace_id : str | None
            Shared trace id for correlating all nodes in the chat pipeline.

        Returns

        Returns
        -------
        list[tuple[str, float]]
            Sorted list of ``(document, score)``, highest score first.
        """
        trace_id = trace_id or uuid.uuid4().hex
        start_ts = time.perf_counter()
        status = "ok"

        result_list: list[tuple[str, float]]
        try:
            result_list = await self._do_rerank(query, documents, top_k)
            status = "ok"
        except Exception as exc:
            logger.warning(
                "Rerank failed unexpectedly, degrading to original documents: %s", exc
            )
            result_list = self._originals_with_score(documents, top_k)
            status = "error"

        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        try:
            log_node(
                trace_id=trace_id,
                node="rerank",
                input_data={
                    "query": query,
                    "document_count": len(documents),
                    "top_k": top_k,
                },
                output_data={
                    "result_count": len(result_list),
                    "results": [
                        {"doc_index": i, "rerank_score": round(score, 4)}
                        for i, (_, score) in enumerate(result_list)
                    ],
                },
                duration_ms=duration_ms,
                service="qwen3-rerank",
                status=status,
                device_id=device_id,
            )
        except Exception as log_exc:
            logger.warning("log_node scheduling failed: %s", log_exc)

        return result_list

    # ── Internal: the actual rerank logic ──────────────────
    async def _do_rerank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """Run rerank with degradation protection."""

        # ── Boundary: empty documents → return immediately ──
        if not documents:
            return []

        # ── Degradation: no API key → skip call, return originals ──
        s = self._settings
        if not s.dashscope_api_key:
            logger.warning(
                "Rerank skipped: DASHSCOPE_API_KEY is empty. "
                "Returning original documents."
            )
            return self._originals_with_score(documents, top_k)

        # ── Build request ───────────────────────────────────
        url = f"{s.rerank_base_url}/reranks"
        payload: dict[str, Any] = {
            "model": s.rerank_model,
            "query": query,
            "documents": documents,
            "top_n": top_k,
        }
        headers = {
            "Authorization": f"Bearer {s.dashscope_api_key}",
            "Content-Type": "application/json",
        }

        # ── Call API with timeout protection ─────────────────
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning(
                "Rerank API call failed, degrading to original documents: %s", exc
            )
            return self._originals_with_score(documents, top_k)

        # ── Parse response ──────────────────────────────────
        try:
            results = data.get("results", [])
            if not results:
                return self._originals_with_score(documents, top_k)

            # Sort by relevance_score descending
            ranked = sorted(
                results,
                key=lambda r: r.get("relevance_score", 0),
                reverse=True,
            )

            output = [
                (documents[r["index"]], float(r.get("relevance_score", 0)))
                for r in ranked
            ]
            return output[:top_k]
        except Exception as exc:
            logger.warning("Rerank response parse failed, degrading: %s", exc)
            return self._originals_with_score(documents, top_k)

    # ── Helper ────────────────────────────────────────────
    @staticmethod
    def _originals_with_score(
        documents: list[str],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """Return original documents (up to top_k) with score 0.0."""
        return [(doc, 0.0) for doc in documents[:top_k]]
