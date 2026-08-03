"""跨方言题库种子（T-002）：将 assessment_data.json 灌入 assessment_questions 表。

兼容 SQLite / MySQL（CloudBase 云数据库）：
- 用 SQLAlchemy Core 跨方言建表 + 插入
- 幂等：表存在且行数>0 则跳过
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)

JSON_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "assessment_data.json"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS assessment_questions (
    id VARCHAR(64) PRIMARY KEY,
    section VARCHAR(32) NOT NULL,
    section_title VARCHAR(128) NOT NULL,
    section_description TEXT,
    type VARCHAR(32) NOT NULL,
    text TEXT NOT NULL,
    options_json TEXT,
    correct_answer TEXT
)
"""


def _load_questions() -> list[tuple]:
    if not JSON_PATH.exists():
        raise FileNotFoundError(f"assessment_data.json 不存在: {JSON_PATH}")
    with open(JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    rows: list[tuple] = []
    for sec in data["sections"]:
        for q in sec["questions"]:
            rows.append((
                q["id"],
                sec["section"],
                sec["title"],
                sec.get("description", ""),
                q["type"],
                q["text"],
                json.dumps(q.get("options", []), ensure_ascii=False),
                q.get("correct_answer"),
            ))
    return rows


async def seed_assessment_data(database_url: str | None = None) -> int:
    """建表（若缺）+ 灌入 46 题；返回插入数。幂等：已有数据则跳过。"""
    from app.config import get_settings
    url = database_url or get_settings().effective_database_url
    engine: AsyncEngine = create_async_engine(url, echo=False)

    inserted = 0
    try:
        async with engine.begin() as conn:
            # 建表（MySQL 需先建库，表若存在则跳过）
            await conn.execute(text(_CREATE_TABLE))

            # 幂等检查：表已有数据则不重复灌
            try:
                existing = await conn.execute(
                    text("SELECT COUNT(*) FROM assessment_questions")
                )
                count = existing.scalar() or 0
            except Exception:
                count = 0

            if count > 0:
                logger.info("[seed] assessment_questions 已有 %d 行，跳过", count)
                return 0

            rows = _load_questions()
            for row in rows:
                await conn.execute(
                    text(
                        "INSERT INTO assessment_questions "
                        "(id, section, section_title, section_description, type, text, options_json, correct_answer) "
                        "VALUES (:id, :section, :section_title, :section_description, :type, :text, :options_json, :correct_answer)"
                    ),
                    {
                        "id": row[0], "section": row[1], "section_title": row[2],
                        "section_description": row[3], "type": row[4], "text": row[5],
                        "options_json": row[6], "correct_answer": row[7],
                    },
                )
            inserted = len(rows)
            logger.info("[seed] 灌入 %d 题", inserted)
    finally:
        await engine.dispose()

    return inserted


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_assessment_data())
