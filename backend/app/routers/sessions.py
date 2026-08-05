"""Session management router: list sessions, query message history.

R-002 访客会话列表：
- 登录用户：仅看自己的会话（user_id 归属）
- 访客（X-Device-ID）：仅看自己设备的会话（device_id 归属）
- 管理员登录：查看全部会话
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session as SessionModel
from app.models import User
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

_service = SessionService()

ADMIN_USER_ID = 1
_bearer = HTTPBearer(auto_error=False)


# ── 可选认证：登录用户 or 访客（X-Device-ID）──────────────
class Identity(BaseModel):
    user_id: int | None = None
    device_id: str | None = None
    is_admin: bool = False
    is_guest: bool = True


async def get_identity(
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_device_id: Annotated[str | None, Header(alias="X-Device-ID")] = None,
) -> Identity:
    """JWT 优先；无 token 用 X-Device-ID 访客；两者皆无 → 空身份（返回空列表）。"""
    if creds is not None:
        try:
            from jose import jwt as jose_jwt
            from app.config import get_settings
            s = get_settings()
            payload = jose_jwt.decode(
                creds.credentials, s.secret_key, algorithms=[s.algorithm]
            )
            email = payload.get("sub")
            if email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user is not None:
                    return Identity(
                        user_id=user.id,
                        is_admin=(user.id == ADMIN_USER_ID),
                        is_guest=False,
                    )
        except Exception:
            pass  # 无效 token → 降级访客

    device_id = (x_device_id or "").strip()
    return Identity(device_id=device_id or None, is_guest=True)


IdentityDep = Annotated[Identity, Depends(get_identity)]


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
    identity: IdentityDep,
    db: AsyncSession = Depends(get_db),
):
    """列出会话：管理员看全部；登录用户看自己的；访客看自己设备的。"""
    if identity.is_admin:
        # 管理员：全部会话
        sessions = await _service.list_all_sessions(db)
    elif identity.is_guest and identity.device_id:
        # 访客：仅本设备
        sessions = await _service.list_device_sessions(db, identity.device_id)
    elif identity.user_id is not None:
        # 登录普通用户：仅自己
        sessions = await _service.list_user_sessions(db, identity.user_id)
    else:
        sessions = []
    return SessionsResponse(sessions=sessions)  # type: ignore[arg-type]


# ── GET /api/sessions/{session_id}/messages ────────────────
@router.get("/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(
    session_id: str,
    identity: IdentityDep,
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
    # Validate session exists + belongs to current user / device / admin
    session = await _service.validate_session_owner(
        db, session_id, identity.user_id, identity.device_id, identity.is_admin
    )
    if session is None:
        # Check if session exists at all (regardless of owner) for 404 vs 403
        exists_result = await db.execute(
            select(SessionModel.id).where(SessionModel.id == session_id)
        )
        if exists_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=403, detail="Forbidden")

    messages = await _service.get_session_messages(db, session_id, limit, before)
    return MessagesResponse(messages=messages)  # type: ignore[arg-type]
