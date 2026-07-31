"""Log-dashboard admin router (P1). Skeleton — placeholder responses."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.admin.deps import verify_admin

router = APIRouter(prefix="/api/admin", tags=["admin-logs"])


@router.get("/dashboard")
async def get_dashboard(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Return dashboard metrics: today requests, refusal rate, trends, intent dist."""
    return {
        "code": 0,
        "data": {
            "metrics": {
                "today_requests": 0,
                "refusal_rate": 0.0,
                "avg_response_ms": 0,
                "total_logs": 0,
            },
            "trends": [],
            "intent_distribution": {},
        },
        "msg": "success",
    }


@router.post("/logs/{trace_id}/badcase")
async def mark_badcase(
    trace_id: str,
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Mark a trace as a bad case (create BadCase row)."""
    return {"code": 0, "data": {"ok": True, "trace_id": trace_id}, "msg": "success"}
