"""Admin auth dependency: only the built-in admin (admin@app.com / id=1) passes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.models import User
from app.routers.auth import get_current_user

ADMIN_EMAIL = "admin@app.com"
ADMIN_USER_ID = 1


async def verify_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Reject any user that is not the built-in admin account."""
    if current_user.id != ADMIN_USER_ID or current_user.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
