"""Bad-case (data flywheel) admin router (P2): list/get/update/generate/store."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.admin.deps import verify_admin
from app.schemas.admin.bad_case_schemas import BadCaseUpdateIn
from app.services.admin.bad_case_service import BadCaseService

router = APIRouter(prefix="/api/admin/bad-cases", tags=["admin-bad-cases"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(verify_admin)]

_service = BadCaseService()


@router.get("")
async def list_bad_cases(
    _admin: AdminDep,
    db: DbDep,
    status: str | None = Query(default=None),
    intent: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List bad cases (supports status / intent filtering)."""
    try:
        data = await _service.list_bad_cases(db, status, intent, limit, offset)
        return {"code": 0, "data": data, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.get("/{bad_case_id}")
async def get_bad_case(
    bad_case_id: int,
    _admin: AdminDep,
    db: DbDep,
):
    """Get a single bad case detail."""
    try:
        bad_case = await _service.get_bad_case(db, bad_case_id)
        if bad_case is None:
            return {"code": 404, "data": None, "msg": "Bad Case 不存在"}
        return {"code": 0, "data": _service._to_dict(bad_case), "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.put("/{bad_case_id}")
async def update_bad_case(
    bad_case_id: int,
    body: BadCaseUpdateIn,
    _admin: AdminDep,
    db: DbDep,
):
    """Update bad case status / ideal answer."""
    try:
        bad_case = await _service.get_bad_case(db, bad_case_id)
        if bad_case is None:
            return {"code": 404, "data": None, "msg": "Bad Case 不存在"}
        data = await _service.update_bad_case(
            db, bad_case, body.status, body.ideal_answer, _admin.email
        )
        return {"code": 0, "data": data, "msg": "success"}
    except ValueError as exc:
        return {"code": 400, "data": None, "msg": str(exc)}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/{bad_case_id}/generate")
async def generate_bad_case_draft(
    bad_case_id: int,
    _admin: AdminDep,
    db: DbDep,
):
    """AI-generate a knowledge draft from a bad case."""
    try:
        bad_case = await _service.get_bad_case(db, bad_case_id)
        if bad_case is None:
            return {"code": 404, "data": None, "msg": "Bad Case 不存在"}
        draft = await _service.generate_draft(db, bad_case)
        return {"code": 0, "data": {"draft": draft}, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/{bad_case_id}/store")
async def store_bad_case(
    bad_case_id: int,
    _admin: AdminDep,
    db: DbDep,
):
    """Save generated draft into knowledge base + rebuild index."""
    try:
        bad_case = await _service.get_bad_case(db, bad_case_id)
        if bad_case is None:
            return {"code": 404, "data": None, "msg": "Bad Case 不存在"}
        # Re-generate draft if none saved yet
        draft = bad_case.ideal_answer
        if not draft:
            draft = await _service.generate_draft(db, bad_case)
        result = await _service.store_bad_case(db, bad_case, draft, _admin.email)
        return {"code": 0, "data": result, "msg": "success"}
    except ValueError as exc:
        return {"code": 400, "data": None, "msg": str(exc)}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}
