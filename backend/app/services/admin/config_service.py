"""System configuration service: key-value config with DB persistence.

Used for admin-editable refusal phrases (useful=false fixed copy) and other
runtime-tunable text. Values are cached in-memory and refreshed on write.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SystemConfig

logger = logging.getLogger(__name__)

# Defaults for known config keys (applied on first read if row missing)
DEFAULT_CONFIG: dict[str, dict[str, str]] = {
    "refuse_uncovered": {
        "default": "暂时不能回答这个问题",
        "desc": "知识库未覆盖时的拒答话术",
    },
    "refuse_insufficient": {
        "default": "信息不足，无法回答该问题",
        "desc": "信息不足时的拒答话术",
    },
}

# In-memory cache so LLM path avoids a DB hit per request
_cache: dict[str, str] = {}


class ConfigService:
    """DB-backed key-value configuration with read cache."""

    async def get_all(self, db: AsyncSession) -> dict[str, Any]:
        result = await db.execute(select(SystemConfig))
        rows = result.scalars().all()
        data: dict[str, Any] = {}
        for row in rows:
            data[row.key] = {
                "key": row.key,
                "value": row.value,
                "description": row.description,
            }
            _cache[row.key] = row.value
        # Fill defaults that are missing (never persisted until edited)
        for key, meta in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = {
                    "key": key,
                    "value": meta["default"],
                    "description": meta["desc"],
                }
        return data

    async def get(self, db: AsyncSession, key: str) -> str:
        if key in _cache:
            return _cache[key]
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        row = result.scalar_one_or_none()
        if row is not None:
            _cache[key] = row.value
            return row.value
        if key in DEFAULT_CONFIG:
            return DEFAULT_CONFIG[key]["default"]
        return ""

    async def set(
        self, db: AsyncSession, key: str, value: str, description: str | None = None
    ) -> dict:
        result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            row = SystemConfig(
                key=key,
                value=value,
                description=description or DEFAULT_CONFIG.get(key, {}).get("desc"),
            )
            db.add(row)
        else:
            row.value = value
            if description is not None:
                row.description = description
        await db.commit()
        _cache[key] = value
        logger.info("Config %s updated", key)
        return {"key": key, "value": value}

    def reset_cache(self) -> None:
        _cache.clear()


# Module-level singleton
config_service = ConfigService()


def get_config_value(key: str) -> str:
    """Synchronous accessor for LLM hot path (uses cached value)."""
    if key in _cache:
        return _cache[key]
    if key in DEFAULT_CONFIG:
        return DEFAULT_CONFIG[key]["default"]
    return ""
