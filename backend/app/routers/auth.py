"""Authentication router: login, JWT issuance, and current-user dependency.

Security rules enforced:
  * Passwords are verified with bcrypt — never stored or compared in plain text.
  * All login failures (user-not-found, password-mismatch) return the same
    ``Invalid credentials`` message to prevent user-enumeration attacks.
  * JWT secret is read from ``config.Settings.secret_key`` — never hardcoded.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

# OAuth2 bearer scheme — extracts token from ``Authorization: Bearer <token>``
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── Pydantic schemas ─────────────────────────────────────
class LoginRequest(BaseModel):
    """Login payload: email + 6-digit numeric password."""

    email: str
    password: str

    @field_validator("password")
    @classmethod
    def password_must_be_6_digits(cls, v: str) -> str:
        if len(v) != 6 or not v.isdigit():
            raise ValueError("Password must be exactly 6 digits")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str


# ── Helpers ──────────────────────────────────────────────
def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt-verify *plain* against a stored *hashed* value."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Issue a JWT with expiry read from ``Settings.access_token_expire_minutes``."""
    to_encode = data.copy()
    s = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=s.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, s.secret_key, algorithm=s.algorithm)


# ── Routes ───────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + 6-digit password and return a JWT token."""
    try:
        result = await db.execute(select(User).where(User.email == request.email))
        user = result.scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001
        # MySQL 连接/查询失败（VPC 不通 / 临时故障）→ 503 而非 401
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database temporarily unavailable: {exc}",
            headers={"Retry-After": "5"},
        )

    # Unified error — never reveal whether the email exists or password is wrong
    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "user_id": user.id}
    )
    s = get_settings()
    return TokenResponse(
        access_token=access_token,
        expires_in=s.access_token_expire_minutes * 60,
        user_id=user.id,
    )


@router.get("/me", response_model=UserOut)
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return the currently authenticated user's profile (protected endpoint)."""
    return current_user


# ── Dependencies (importable by other routers) ────────────
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode the JWT and return the matching ``User`` row, or raise 401.

    Used as a FastAPI dependency on protected endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        s = get_settings()
        payload = jwt.decode(token, s.secret_key, algorithms=[s.algorithm])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
