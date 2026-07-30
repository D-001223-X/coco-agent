"""Log query router: list trace summaries, view full chain details.

All endpoints require JWT authentication.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.services.log_service import LogService

router = APIRouter(prefix="/api/logs", tags=["logs"])

_service = LogService()


# ── Schemas ──────────────────────────────────────────────
class LogSummaryOut(BaseModel):
    id: int
    trace_id: str
    user_id: int | None = None
    question: str = ""
    intent: str = ""
    created_at: str | None = None


class LogListResponse(BaseModel):
    logs: list[LogSummaryOut]


class NodeDetail(BaseModel):
    node: str
    input_data: object | None = None
    output_data: object | None = None
    duration_ms: int | None = None
    service: str = ""
    status: str = ""


class TraceDetailResponse(BaseModel):
    trace_id: str
    user_id: int | None = None
    nodes: list[NodeDetail]


# ── GET /api/logs ──────────────────────────────────────────
@router.get("", response_model=LogListResponse)
async def list_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all trace summaries, grouped by trace_id, newest first."""
    traces = await _service.list_traces(db)
    return LogListResponse(logs=traces)


# ── GET /api/logs/{trace_id} ───────────────────────────────
@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_log_detail(
    trace_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Get the full chain detail for a specific trace_id."""
    detail = await _service.get_trace_detail(db, trace_id)
    # Return default structure if trace not found (no 404)
    if not detail["nodes"]:
        return TraceDetailResponse(trace_id=trace_id, user_id=None, nodes=[])
    return TraceDetailResponse(**detail)
