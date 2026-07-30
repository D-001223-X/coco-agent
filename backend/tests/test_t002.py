"""T-002: Login & JWT authentication tests.

Covers 5 scenarios:
  1. Normal login → 200 + JWT token
  2. Wrong password → 401 "Invalid credentials"
  3. Wrong email   → 401 "Invalid credentials"
  4. Password length error → 422 (validation)
  5. Invalid token → 401 "Invalid credentials"
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import ADMIN_EMAIL, ADMIN_PASSWORD, get_db, init_db
from app.main import app


# ── Fixture: test database + HTTP client ─────────────────
@pytest_asyncio.fixture
async def client(tmp_path):
    """Spin up a temp SQLite DB, seed admin, and override get_db."""
    db_path = tmp_path / "test_t002.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # Create tables + seed admin user
    await init_db(database_url=db_url)

    # Create a persistent engine for queries during tests
    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


# ── Test 1: Normal login ─────────────────────────────────
async def test_login_success(client):
    """Admin logs in with correct email + 6-digit password → 200 + token."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


# ── Test 2: Wrong password ───────────────────────────────
async def test_login_wrong_password(client):
    """Correct email, wrong password → 401 + unified error message."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "999999"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


# ── Test 3: Wrong email ──────────────────────────────────
async def test_login_wrong_email(client):
    """Non-existent email → 401 + same unified error (no enumeration)."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@app.com", "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


# ── Test 4: Password length error ────────────────────────
async def test_login_wrong_password_length(client):
    """Password shorter than 6 digits → 422 validation error."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "123"},
    )
    assert resp.status_code == 422


# ── Test 5: Invalid token ───────────────────────────────
async def test_invalid_token(client):
    """Accessing a protected endpoint with a bogus token → 401."""
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid-jwt-token"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"
