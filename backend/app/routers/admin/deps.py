"""Admin auth dependency: only the built-in admin (admin@app.com / id=1) passes.

T-003 访客只读模式：
- ``verify_admin``：所有 admin 接口（GET 与写操作）都必须管理员登录。
- ``admin_read_guest_ok``：GET 请求未登录/非管理员时放行为「只读访客」
  （返回一个占位 User），写操作（POST/PUT/DELETE）仍强制 verify_admin。
  这样访客能查看后台内容、不能编辑（前端配合禁用按钮）。
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@app.com"
ADMIN_USER_ID = 1

_bearer = HTTPBearer(auto_error=False)

# 只读访客占位 User（ID 为 0 不会与真实用户冲突）
_GUEST_USER = User(id=0, email="guest@readonly", role="guest", hashed_password="")


def _is_admin(user: User | None) -> bool:
    return user is not None and user.id == ADMIN_USER_ID and user.email == ADMIN_EMAIL


async def _optional_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """解析 token；无 token/无效 → None（不抛 401）。"""
    if creds is None:
        return None
    try:
        from jose import jwt as jose_jwt
        from app.config import get_settings
        s = get_settings()
        payload = jose_jwt.decode(
            creds.credentials, s.secret_key, algorithms=[s.algorithm]
        )
        email = payload.get("sub")
        if not email:
            return None
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001
        logger.debug("[admin] token parse skipped: %s", exc)
        return None


async def verify_admin(
    current_user: Annotated[User, Depends(_optional_current_user)],
) -> User:
    """Reject any user that is not the built-in admin account."""
    if not _is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


async def admin_read_guest_ok(
    request: Request,
    current_user: Annotated[User | None, Depends(_optional_current_user)],
) -> User:
    """GET 请求允许未登录/非管理员以只读访客身份访问；写操作强制管理员。"""
    # 非 GET 写操作 → 必须管理员
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not _is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user
    # 读操作：已登录管理员 → 本人；否则 → 只读访客占位
    if _is_admin(current_user):
        return current_user
    return _GUEST_USER
