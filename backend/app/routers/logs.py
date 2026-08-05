"""Log query router: list trace summaries, view full chain details.

R-003 访客日志列表：
- 管理员登录：查看全部日志
- 登录普通用户：仅自己的日志（user_id 归属）
- 访客（X-Device-ID）：仅自己设备的日志（device_id 归属）
- 无身份：空列表
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services.log_service import LogService

router = APIRouter(prefix="/api/logs", tags=["logs"])

_service = LogService()

ADMIN_USER_ID = 1
_bearer = HTTPBearer(auto_error=False)


# ── 可选认证：登录用户 or 访客（X-Device-ID）──────────────
class LogIdentity(BaseModel):
    user_id: int | None = None
    device_id: str | None = None
    is_admin: bool = False
    is_guest: bool = True


async def get_log_identity(
    db: Annotated[AsyncSession, Depends(get_db)],
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    x_device_id: Annotated[str | None, Header(alias="X-Device-ID")] = None,
) -> LogIdentity:
    """JWT 优先；无 token 用 X-Device-ID 访客；两者皆无 → 空身份。"""
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
                    return LogIdentity(
                        user_id=user.id,
                        is_admin=(user.id == ADMIN_USER_ID),
                        is_guest=False,
                    )
        except Exception:
            pass  # 无效 token → 降级访客

    device_id = (x_device_id or "").strip()
    return LogIdentity(device_id=device_id or None, is_guest=True)


LogIdentityDep = Annotated[LogIdentity, Depends(get_log_identity)]


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
    identity: LogIdentityDep,
    db: AsyncSession = Depends(get_db),
):
    """列出 trace 摘要（按身份过滤），newest first。"""
    if identity.is_admin:
        traces = await _service.list_traces(db)
    elif identity.is_guest and identity.device_id:
        traces = await _service.list_traces(db, device_id=identity.device_id)
    elif identity.user_id is not None:
        traces = await _service.list_traces(db, user_id=identity.user_id)
    else:
        traces = []
    return LogListResponse(logs=traces)


# ── GET /api/logs/{trace_id} ───────────────────────────────
@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_log_detail(
    trace_id: str,
    identity: LogIdentityDep,
    db: AsyncSession = Depends(get_db),
):
    """获取单个 trace 的完整链路详情（按身份过滤归属）。"""
    detail = await _service.get_trace_detail(
        db, trace_id,
        user_id=identity.user_id,
        device_id=identity.device_id,
        is_admin=identity.is_admin,
    )
    # Return default structure if trace not found (no 404)
    if not detail["nodes"]:
        return TraceDetailResponse(trace_id=trace_id, user_id=None, nodes=[])
    return TraceDetailResponse(**detail)
