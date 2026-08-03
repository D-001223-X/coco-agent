"""Retrieval-parameter admin router (P1): get/update/reset + save to .env."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.admin.deps import admin_read_guest_ok
from app.schemas.admin.param_schemas import ParamsUpdateIn
from app.services.admin.param_service import get_param_service

router = APIRouter(prefix="/api/admin/params", tags=["admin-params"])

AdminDep = Annotated[User, Depends(admin_read_guest_ok)]


@router.get("")
async def get_params(
    _admin: AdminDep,
):
    """Return current retrieval parameters."""
    service = get_param_service()
    return {"code": 0, "data": service.get(), "msg": "success"}


@router.put("")
async def update_params(
    body: ParamsUpdateIn,
    _admin: AdminDep,
):
    """Update retrieval parameters (in-memory, immediate effect)."""
    try:
        service = get_param_service()
        updates = body.model_dump(exclude_none=True)
        params = service.update(updates)
        return {"code": 0, "data": params, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/reset")
async def reset_params(
    _admin: AdminDep,
):
    """Reset retrieval parameters to defaults."""
    service = get_param_service()
    params = service.reset()
    return {"code": 0, "data": params, "msg": "success"}


@router.post("/save")
async def save_params_to_env(
    _admin: AdminDep,
):
    """Persist current params into backend/.env."""
    try:
        service = get_param_service()
        result = service.save_to_env()
        return {"code": 0, "data": result, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}
