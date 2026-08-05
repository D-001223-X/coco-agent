"""Practice assessment router (T-002).

Provides:
  GET  /api/practice/assessment/questions  — fetch the full question bank
  POST /api/practice/assessment/submit    — grade answers, return CEFR level
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice/assessment", tags=["practice-assessment"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

# CEFR 等级映射（总分 46 分）
_CEFR_MAP: list[tuple[int, str, str]] = [
    (0, "A1", "入门级：能理解和使用非常基础的短语和表达"),
    (20, "A2", "基础级：能理解最直接相关领域的句子和表达"),
    (30, "B1", "进阶级：能理解工作、学习、休闲等熟悉领域的标准输入"),
    (40, "B2", "中高级：能理解具体和抽象主题的复杂文本"),
]


class SubmitIn(BaseModel):
    answers: dict[str, str]


def _map_cefr(total: int) -> dict[str, str]:
    level = "A1"
    desc = _CEFR_MAP[0][2]
    for threshold, lv, d in _CEFR_MAP:
        if total >= threshold:
            level, desc = lv, d
    return {"cefrLevel": level, "levelDescription": desc}


@router.get("/questions")
async def get_questions(db: DbDep):
    """返回全部题目，按维度分组（不包含正确答案）。

    访客模式：无需登录（移除 UserDep），扫码即用。
    """
    try:
        result = await db.execute(
            text("""
                SELECT id, section, section_title, section_description, type, text, options_json
                FROM assessment_questions
                ORDER BY id
            """)
        )
        rows = result.fetchall()

        sections_map: dict[str, dict[str, Any]] = {}
        for row in rows:
            sec = row.section
            if sec not in sections_map:
                sections_map[sec] = {
                    "section": sec,
                    "title": row.section_title,
                    "description": row.section_description,
                    "questions": [],
                }
            options = json.loads(row.options_json) if row.options_json else []
            sections_map[sec]["questions"].append({
                "id": row.id,
                "type": row.type,
                "text": row.text,
                "options": options,
            })

        # 固定顺序：listening → speaking → reading
        order = ["listening", "speaking", "reading"]
        sections = [sections_map[s] for s in order if s in sections_map]
        for s in sections_map.values():
            if s["section"] not in order:
                sections.append(s)

        return {"code": 0, "data": {"sections": sections}, "msg": "success"}
    except Exception as exc:
        logger.error("get_questions failed: %s", exc)
        return {"code": 500, "data": None, "msg": f"获取题目失败: {exc}"}


@router.post("/submit")
async def submit_assessment(body: SubmitIn, db: DbDep):
    """批改答案：听力/阅读自动批改，口语按完成度计分。

    访客模式：无需登录（移除 UserDep）。
    """
    try:
        result = await db.execute(
            text("SELECT id, section, correct_answer, type FROM assessment_questions")
        )
        rows = result.fetchall()
        q_map = {row.id: row for row in rows}

        listening = speaking = reading = 0
        for qid, answer in body.answers.items():
            row = q_map.get(qid)
            if row is None:
                continue
            if row.type == "multiple_choice":
                if answer and answer.strip() == (row.correct_answer or "").strip():
                    if row.section == "listening":
                        listening += 1
                    else:
                        reading += 1
            else:  # text (口语)：完成度计分
                if answer and answer.strip():
                    speaking += 1

        total = listening + speaking + reading
        cefr = _map_cefr(total)

        return {
            "code": 0,
            "data": {
                "listeningScore": listening,
                "speakingScore": speaking,
                "readingScore": reading,
                "totalScore": total,
                **cefr,
            },
            "msg": "success",
        }
    except Exception as exc:
        logger.error("submit_assessment failed: %s", exc)
        return {"code": 500, "data": None, "msg": f"提交失败: {exc}"}
