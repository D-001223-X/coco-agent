"""Bad-case (data flywheel) service: CRUD + AI draft generation + store-to-KB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, BadCase
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Knowledge base file (repo root /knowledge_base/coco_knowledge.md)
KB_PATH = Path(__file__).resolve().parent.parent.parent.parent.parent / "knowledge_base" / "coco_knowledge.md"

DRAFT_PROMPT = """你是一个知识库编辑助手。请根据以下用户问题和系统回答，生成一个知识库条目。

用户问题：{question}
系统回答：{answer}

请生成 Markdown 格式的知识条目，包含：
- 一个清晰的标题（用 ##）
- 回答内容（用 - 列表，不超过100字）
"""


class BadCaseService:
    """CRUD + flywheel operations for BadCase rows."""

    # ── List (with filters) ────────────────────────────────
    async def list_bad_cases(
        self,
        db: AsyncSession,
        status: str | None = None,
        intent: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        stmt = select(BadCase).order_by(BadCase.id.desc()).limit(limit).offset(offset)
        if status:
            stmt = select(BadCase).where(BadCase.status == status).order_by(BadCase.id.desc()).limit(limit).offset(offset)
        if intent:
            stmt = select(BadCase).where(BadCase.intent == intent).order_by(BadCase.id.desc()).limit(limit).offset(offset)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        count_stmt = select(BadCase.id)
        if status:
            count_stmt = count_stmt.where(BadCase.status == status)
        if intent:
            count_stmt = count_stmt.where(BadCase.intent == intent)
        total_result = await db.execute(count_stmt)
        total = len(total_result.scalars().all())

        items = [self._to_dict(r) for r in rows]
        return {"items": items, "total": total}

    @staticmethod
    def _to_dict(r: BadCase) -> dict:
        return {
            "id": r.id,
            "trace_id": r.trace_id,
            "user_question": r.user_question,
            "system_answer": r.system_answer,
            "intent": r.intent,
            "source": r.source,
            "status": r.status,
            "ideal_answer": r.ideal_answer,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "calibrated_by": r.calibrated_by,
            "stored_at": r.stored_at.isoformat() if r.stored_at else None,
        }

    # ── Get one ────────────────────────────────────────────
    async def get_bad_case(self, db: AsyncSession, bad_case_id: int) -> BadCase | None:
        result = await db.execute(select(BadCase).where(BadCase.id == bad_case_id))
        return result.scalar_one_or_none()

    # ── Update status / ideal answer ───────────────────────
    async def update_bad_case(
        self,
        db: AsyncSession,
        bad_case: BadCase,
        status: str | None,
        ideal_answer: str | None,
        user_email: str,
    ) -> dict:
        valid_statuses = {"pending", "calibrated", "stored", "ignored"}
        if status and status not in valid_statuses:
            raise ValueError(f"非法状态: {status}")

        old_status = bad_case.status
        if status:
            bad_case.status = status
        if ideal_answer is not None:
            bad_case.ideal_answer = ideal_answer
            bad_case.calibrated_by = user_email
            if bad_case.status == "pending":
                bad_case.status = "calibrated"
        await db.commit()
        await db.refresh(bad_case)

        db.add(AuditLog(
            action="update_badcase",
            detail=f"bad_case#{bad_case.id} {old_status}→{bad_case.status}",
            user_email=user_email,
        ))
        await db.commit()
        return self._to_dict(bad_case)

    # ── AI draft generation ────────────────────────────────
    async def generate_draft(self, db: AsyncSession, bad_case: BadCase) -> str:
        llm = LLMService()
        prompt = DRAFT_PROMPT.format(
            question=bad_case.user_question,
            answer=bad_case.system_answer or "",
        )
        result = await llm._call_deepseek(bad_case.user_question, [], prompt)
        return result

    # ── Store into knowledge base + rebuild index ─────────
    async def store_bad_case(
        self,
        db: AsyncSession,
        bad_case: BadCase,
        draft: str,
        user_email: str,
    ) -> dict:
        # 1. Append draft to knowledge base file
        content = draft.strip()
        if not content:
            raise ValueError("草稿为空，无法入库")

        KB_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = KB_PATH.read_text(encoding="utf-8") if KB_PATH.exists() else ""
        with KB_PATH.open("a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(f"\n{content}\n")

        # 2. Rebuild index
        from scripts.build_index import main as build_main
        try:
            await build_main()
        except Exception as exc:
            logger.error("Rebuild after store failed: %s", exc)

        # 3. Update bad case status → stored
        bad_case.status = "stored"
        bad_case.ideal_answer = content
        bad_case.calibrated_by = user_email
        bad_case.stored_at = datetime.now(timezone.utc)
        await db.commit()

        # 4. Audit log
        db.add(AuditLog(
            action="store_badcase",
            detail=f"bad_case#{bad_case.id} → knowledge_base 入库",
            user_email=user_email,
        ))
        await db.commit()
        return {"ok": True, "bad_case_id": bad_case.id, "stored_at": bad_case.stored_at.isoformat()}
