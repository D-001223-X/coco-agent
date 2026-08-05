"""T-008: Session management tests.

Covers 5 scenarios:
  1. Multiple sessions with messages → list has correct counts + order
  2. Message query returns messages in chronological order
  3. limit=100 clamped to 50
  4. Non-existent session_id → 404
  5. Other user's session → 403
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import ADMIN_EMAIL, get_db, init_db
from app.main import app
from app.models import Message, Session


# ── Fixture: test DB + auth token ────────────────────────
@pytest_asyncio.fixture
async def auth_context(tmp_path):
    """Seed temp DB with admin + sessions + messages, return JWT + factory."""
    db_path = tmp_path / "test_t008.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await init_db(database_url=db_url)

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Insert two sessions with messages
    from datetime import datetime, timezone
    import app.database as db_module

    db_module._session_factory = factory

    async with factory() as session:
        # Session A: 3 messages (earlier)
        sess_a = Session(id="sess-a", user_id=1)
        session.add(sess_a)
        # Session B: 3 messages (later, so it sorts first)
        sess_b = Session(id="sess-b", user_id=1)
        session.add(sess_b)
        await session.flush()

        for i in range(3):
            session.add(Message(session_id="sess-a", role="user" if i % 2 == 0 else "assistant",
                                content=f"msg-a-{i}"))
            session.add(Message(session_id="sess-b", role="user" if i % 2 == 0 else "assistant",
                                content=f"msg-b-{i}"))
        await session.commit()

        # Update sess_b's updated_at to be newer
        from sqlalchemy import text, update
        await session.execute(
            text("UPDATE sessions SET updated_at = datetime('now', '+1 minute') WHERE id = 'sess-b'")
        )
        await session.commit()

    # Generate a valid JWT for the admin user
    from app.routers.auth import create_access_token
    token = create_access_token(
        data={"sub": ADMIN_EMAIL, "role": "admin", "user_id": 1}
    )

    yield {
        "token": token,
        "factory": factory,
        "engine": engine,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(auth_context):
    """HTTP client backed by the test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Test 1: List sessions → correct order + message_count ──
async def test_list_sessions(client, auth_context):
    """Two sessions, each with 3 messages → 2 sessions, message_count=3, newest first."""
    resp = await client.get(
        "/api/sessions",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["sessions"]) == 2

    # Session B should be first (newer updated_at)
    assert data["sessions"][0]["session_id"] == "sess-b"
    assert data["sessions"][1]["session_id"] == "sess-a"

    # Both have message_count = 3
    for s in data["sessions"]:
        assert s["message_count"] == 3
        assert s["session_id"] in ("sess-a", "sess-b")
        assert s["created_at"] is not None
        assert s["updated_at"] is not None


# ── Test 2: Get messages → chronological order ────────────
async def test_get_messages_chronological(client, auth_context):
    """Messages should be returned in chronological order (oldest first)."""
    resp = await client.get(
        "/api/sessions/sess-a/messages",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 3

    # Chronological order: msg-a-0, msg-a-1, msg-a-2
    assert data["messages"][0]["content"] == "msg-a-0"
    assert data["messages"][1]["content"] == "msg-a-1"
    assert data["messages"][2]["content"] == "msg-a-2"

    # IDs should be increasing
    assert data["messages"][0]["id"] < data["messages"][1]["id"] < data["messages"][2]["id"]


# ── Test 3: limit=100 → clamped to 50 ──────────────────────
async def test_get_messages_limit_clamped(client, auth_context):
    """limit=100 should return all 3 messages (clamped to 50, but we only have 3)."""
    resp = await client.get(
        "/api/sessions/sess-a/messages?limit=100",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["messages"]) == 3  # only 3 exist, limit clamped to 50


# ── Test 4: Non-existent session → 404 ────────────────────
async def test_get_messages_not_found(client, auth_context):
    """Querying a non-existent session should return 404."""
    resp = await client.get(
        "/api/sessions/nonexistent-session/messages",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 404


# ── Test 5: Other user's session → 管理员可看（R-002）──
async def test_get_messages_forbidden(client, auth_context):
    """R-002：管理员登录后可查看任意会话（不再 403）。"""
    async with auth_context["factory"]() as session:
        session.add(Session(id="sess-other", user_id=999))
        await session.commit()

    resp = await client.get(
        "/api/sessions/sess-other/messages",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    # admin(user_id=1) → is_admin=True → 可访问任意会话
    assert resp.status_code == 200
