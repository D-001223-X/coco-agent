"""Log-dashboard admin router (P1): dashboard metrics + mark bad case."""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AuditLog, BadCase, Log, User
from app.routers.admin.deps import verify_admin
from app.services.admin.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin-logs"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(verify_admin)]

_dashboard_service = DashboardService()


@router.get("/dashboard")
async def get_dashboard(
    _admin: AdminDep,
    db: DbDep,
):
    """Return dashboard metrics: today requests, refusal rate, trends, intent dist."""
    try:
        data = await _dashboard_service.get_dashboard(db)
        return {"code": 0, "data": data, "msg": "success"}
    except Exception as exc:
        logger.error("Dashboard error: %s", exc, exc_info=True)
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/logs/{trace_id}/badcase")
async def mark_badcase(
    trace_id: str,
    _admin: AdminDep,
    db: DbDep,
):
    """Mark a trace as a bad case: create a BadCase row (idempotent)."""
    try:
        # Reject if already exists
        existing = await db.execute(
            select(BadCase).where(BadCase.trace_id == trace_id)
        )
        if existing.scalar_one_or_none() is not None:
            return {"code": 0, "data": {"ok": True, "already_exists": True}, "msg": "success"}

        # Gather question from the trace's intent_recognition node
        question = trace_id
        answer = None
        intent = None
        result = await db.execute(
            select(Log).where(Log.trace_id == trace_id).order_by(Log.created_at.asc())
        )
        logs = result.scalars().all()
        for log in logs:
            try:
                input_data = json.loads(log.input_data) if log.input_data else {}
                output_data = json.loads(log.output_data) if log.output_data else {}
            except (json.JSONDecodeError, TypeError):
                input_data, output_data = {}, {}
            if log.node == "intent_recognition":
                question = input_data.get("query", trace_id)
                intent = output_data.get("intent")
            elif log.node in ("llm_generate", "llm_generation"):
                answer = output_data.get("content") or input_data.get("answer")

        bad_case = BadCase(
            trace_id=trace_id,
            user_question=question,
            system_answer=answer,
            intent=intent,
            source="manual",
            status="pending",
        )
        db.add(bad_case)
        await db.commit()
        await db.refresh(bad_case)

        # Audit log
        db.add(AuditLog(
            action="mark_badcase",
            detail=f"trace_id={trace_id} → bad_case#{bad_case.id}",
            user_email=_admin.email,
        ))
        await db.commit()

        return {"code": 0, "data": {"ok": True, "bad_case_id": bad_case.id}, "msg": "success"}
    except Exception as exc:
        logger.error("Mark badcase error: %s", exc, exc_info=True)
        return {"code": 500, "data": None, "msg": str(exc)}
