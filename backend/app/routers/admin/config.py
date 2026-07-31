"""System-config admin router (P2): refusal phrases etc. as key-value config."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.admin.deps import verify_admin
from app.services.admin.config_service import config_service

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(verify_admin)]


class ConfigUpdateIn(BaseModel):
    value: str
    description: str | None = None


@router.get("/refuse-phrases")
async def get_refuse_phrases(
    _admin: AdminDep,
    db: DbDep,
):
    """Return the refusal phrase configs (uncovered / insufficient)."""
    try:
        data = await config_service.get_all(db)
        refuse = {
            k: v for k, v in data.items() if k in ("refuse_uncovered", "refuse_insufficient")
        }
        return {"code": 0, "data": refuse, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.put("/refuse-phrases/{key}")
async def update_refuse_phrase(
    key: str,
    body: ConfigUpdateIn,
    _admin: AdminDep,
    db: DbDep,
):
    """Update a refusal phrase config."""
    try:
        if key not in ("refuse_uncovered", "refuse_insufficient"):
            return {"code": 400, "data": None, "msg": "未知配置项"}
        result = await config_service.set(db, key, body.value, body.description)
        return {"code": 0, "data": result, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}
