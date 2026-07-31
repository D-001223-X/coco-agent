"""Retrieval-parameter admin router (P1). Skeleton — placeholder responses."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.admin.deps import verify_admin

router = APIRouter(prefix="/api/admin/params", tags=["admin-params"])


@router.get("")
async def get_params(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Return current retrieval parameters."""
    return {
        "code": 0,
        "data": {
            "faiss_top_k": 20,
            "fts5_top_k": 20,
            "threshold": 0.3,
            "rrf_k": 60,
            "final_top_k": 3,
        },
        "msg": "success",
    }


@router.put("")
async def update_params(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Update retrieval parameters (in-memory, immediate effect)."""
    return {"code": 0, "data": {"updated": True}, "msg": "success"}


@router.post("/reset")
async def reset_params(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Reset retrieval parameters to defaults."""
    return {"code": 0, "data": {"reset": True}, "msg": "success"}
