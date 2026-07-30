"""Session management router: list sessions, query message history.

All endpoints require JWT authentication (``Depends(get_current_user)``).
Users can only access their own sessions — cross-user access returns 403.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_service = SessionService()


# ── Schemas ──────────────────────────────────────────────
class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str | None = None


class MessagesResponse(BaseModel):
    messages: list[MessageOut]


class SessionItem(BaseModel):
    session_id: str
    created_at: str | None = None
    updated_at: str | None = None
    message_count: int


class SessionsResponse(BaseModel):
    sessions: list[SessionItem]


# ── GET /api/sessions ──────────────────────────────────────
@router.get("", response_model=SessionsResponse)
async def list_sessions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """List all sessions belonging to the authenticated user (newest first)."""
    sessions = await _service.list_user_sessions(db, current_user.id)
    return SessionsResponse(sessions=sessions)  # type: ignore[arg-type]


# ── GET /api/sessions/{session_id}/messages ────────────────
@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(
    session_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1),
    before: int | None = Query(default=None, ge=1),
):
    """Get paginated messages for a session (oldest first).

    Parameters
    ----------
    limit : int
        Max messages to return (default 50, max clamped to 50).
    before : int | None
        Cursor: return only messages with ``id < before``.
        If omitted, returns the latest *limit* messages.
    """
    # Clamp limit to max 50
    limit = min(limit, 50)
    # Validate session exists + belongs to current user
    session = await _service.validate_session_owner(db, session_id, current_user.id)
    if session is None:
        # Check if session exists at all (regardless of owner) for 404 vs 403
        from sqlalchemy import select
        from app.models import Session as SessionModel

        exists_result = await db.execute(
            select(SessionModel.id).where(SessionModel.id == session_id)
        )
        if exists_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = await _service.get_session_messages(db, session_id, limit, before)
    return MessagesResponse(messages=messages)  # type: ignore[arg-type]
