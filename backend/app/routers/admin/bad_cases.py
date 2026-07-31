"""Bad-case (data flywheel) admin router (P2). Skeleton — placeholder responses."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.admin.deps import verify_admin

router = APIRouter(prefix="/api/admin/bad-cases", tags=["admin-bad-cases"])


@router.get("")
async def list_bad_cases(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """List bad cases (supports status / intent filtering)."""
    return {"code": 0, "data": {"items": [], "total": 0}, "msg": "success"}


@router.get("/{bad_case_id}")
async def get_bad_case(
    bad_case_id: int,
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Get a single bad case detail."""
    return {"code": 0, "data": {"id": bad_case_id}, "msg": "success"}


@router.put("/{bad_case_id}")
async def update_bad_case(
    bad_case_id: int,
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Update bad case status / ideal answer."""
    return {"code": 0, "data": {"id": bad_case_id, "updated": True}, "msg": "success"}


@router.post("/{bad_case_id}/generate")
async def generate_bad_case_draft(
    bad_case_id: int,
    _admin: Annotated[User, Depends(verify_admin)],
):
    """AI-generate a knowledge draft from a bad case."""
    return {"code": 0, "data": {"draft": ""}, "msg": "success"}


@router.post("/{bad_case_id}/store")
async def store_bad_case(
    bad_case_id: int,
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Save generated draft into knowledge base + rebuild index."""
    return {"code": 0, "data": {"ok": True, "bad_case_id": bad_case_id}, "msg": "success"}
