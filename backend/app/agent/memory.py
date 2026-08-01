"""Agent 记忆模块（T-001 骨架）。

提供短期（会话内）与长期（跨会话）记忆接口。
T-001 阶段实现内存级存储，后续任务可接入数据库持久化。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AgentMemory:
    """轻量内存级记忆存储。"""

    def __init__(self) -> None:
        self._short_term: list[dict[str, Any]] = []  # 短期记忆（按序追加）
        self._long_term: dict[str, Any] = {}  # 长期记忆（key-value）

    # ── 短期记忆 ────────────────────────────────────────
    def add_short_term(self, entry: dict[str, Any]) -> None:
        self._short_term.append(entry)

    def get_short_term(self, limit: int | None = None) -> list[dict[str, Any]]:
        if limit is None:
            return list(self._short_term)
        return list(self._short_term[-limit:])

    # ── 长期记忆 ────────────────────────────────────────
    def set_long_term(self, key: str, value: Any) -> None:
        self._long_term[key] = value

    def get_long_term(self, key: str, default: Any = None) -> Any:
        return self._long_term.get(key, default)

    # ── 生命周期 ────────────────────────────────────────
    def clear(self) -> None:
        self._short_term.clear()
        self._long_term.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "short_term": list(self._short_term),
            "long_term": dict(self._long_term),
        }
