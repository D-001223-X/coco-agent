"""Retrieval-parameter admin service: in-memory tuning + .env persistence."""

from __future__ import annotations

import logging
from pathlib import Path

from app.services.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

# Keys that map 1:1 to .env variable names
ENV_KEY_MAP = {
    "faiss_top_k": "RETRIEVAL_FAISS_TOP_K",
    "fts5_top_k": "RETRIEVAL_FTS5_TOP_K",
    "threshold": "RETRIEVAL_THRESHOLD",
    "rrf_k": "RETRIEVAL_RRF_K",
    "final_top_k": "RETRIEVAL_FINAL_TOP_K",
}

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class ParamService:
    """Fronts a shared RetrievalService instance with persistence helpers."""

    def __init__(self, retrieval: RetrievalService) -> None:
        self._retrieval = retrieval

    # ── In-memory (immediate effect) ───────────────────────
    def get(self) -> dict:
        return self._retrieval.get_params()

    def update(self, params: dict) -> dict:
        return self._retrieval.update_params(params)

    def reset(self) -> dict:
        return self._retrieval.reset_params()

    # ── Persist to .env ────────────────────────────────────
    def save_to_env(self) -> dict:
        """Write current params into backend/.env (idempotent, preserves file)."""
        params = self._retrieval.get_params()

        lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
        env_map = {k: v for k, v in (line.split("=", 1) for line in lines if "=" in line and not line.strip().startswith("#"))}

        for key, value in params.items():
            env_name = ENV_KEY_MAP[key]
            env_map[env_name] = str(value)

        new_lines = [f"{k}={v}" for k, v in env_map.items()]
        ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        logger.info("Params saved to .env: %s", params)
        return {"saved": True, "params": params}


# Shared singleton wrapping the retrieval service instance used by chat.py.
# chat.py imports RetrievalService directly; to keep a single source of truth,
# we mirror its params through this module-level object.
_param_cache: dict | None = None
_retrieval_singleton: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    """Return a shared RetrievalService (same instance as chat pipeline)."""
    global _retrieval_singleton
    if _retrieval_singleton is None:
        _retrieval_singleton = RetrievalService()
    return _retrieval_singleton


def get_param_service() -> ParamService:
    return ParamService(get_retrieval_service())
