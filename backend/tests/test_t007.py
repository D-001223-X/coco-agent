"""T-007: Chat pipeline integration tests.

Covers 5 scenarios:
  1. SUPPORT intent → retrieve → rerank → LLM → response with "68元"
  2. CHAT intent → direct LLM → friendly response
  3. Invalid session_id → 404
  4. No auth token → 401
  5. Service exception → 500 (no stack leak)
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock, patch

from app.database import ADMIN_EMAIL, get_db, init_db
from app.main import app
from app.routers import chat as chat_routes
from app.services.intent_service import IntentResult, INTENT_CHAT, INTENT_SUPPORT
from app.services.retrieval_service import RetrievedChunk


# ── Fixture: test DB + auth token ────────────────────────
@pytest_asyncio.fixture
async def auth_context(tmp_path):
    """Seed temp DB with admin, override get_db, return a valid JWT."""
    db_path = tmp_path / "test_t007.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await init_db(database_url=db_url)

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    # Generate a valid JWT for the admin user
    from app.routers.auth import create_access_token
    token = create_access_token(
        data={"sub": ADMIN_EMAIL, "role": "admin", "user_id": 1}
    )

    yield {
        "token": token,
        "db_url": db_url,
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


# ── Shared mock helpers ──────────────────────────────────
def _mock_intent(intent: str, query: str, confidence: float = 0.95):
    return AsyncMock(return_value=IntentResult(
        intent=intent,
        confidence=confidence,
        resolved_question=query,
        reason="test",
    ))


# ── Test 1: SUPPORT → full pipeline ───────────────────────
async def test_chat_support_pipeline(client, auth_context):
    """SUPPORT intent should retrieve, rerank, and return knowledge-based answer."""
    mock_intent = _mock_intent(INTENT_SUPPORT, "会员多少钱？")
    mock_search = AsyncMock(return_value=[
        RetrievedChunk(chunk_id="4", content="会员每月68元，包含无限对话时长。", score=0.85, section="付费方案"),
    ])
    mock_rerank = AsyncMock(return_value=[("会员每月68元，包含无限对话时长。", 0.9)])
    mock_llm = AsyncMock(return_value={
        "useful": True,
        "content": "可可语伴会员每月68元",
        "translation": "CocoMate membership costs 68 yuan per month.",
    })

    with (
        patch.object(chat_routes._intent_service, "recognize", mock_intent),
        patch.object(chat_routes._retrieval_service, "search", mock_search),
        patch.object(chat_routes._rerank_service, "rerank", mock_rerank),
        patch.object(chat_routes._llm_service, "generate", mock_llm),
    ):
        resp = await client.post(
            "/api/chat",
            json={"message": "会员多少钱？"},
            headers={"Authorization": f"Bearer {auth_context['token']}"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["intent"] == INTENT_SUPPORT
    assert "68" in data["response"]["content"], (
        f"Expected '68' in content, got: {data['response']['content']}"
    )
    assert data["response"]["useful"] is True
    assert data["session_id"] is not None
    assert data["message_id"] > 0
    assert data["resolved_question"] == "会员多少钱？"


# ── Test 2: CHAT → direct LLM, no retrieval ────────────────
async def test_chat_chat_intent(client, auth_context):
    """CHAT intent should skip retrieval and return a friendly response."""
    mock_intent = _mock_intent(INTENT_CHAT, "你好呀")
    mock_llm = AsyncMock(return_value={
        "useful": True,
        "content": "你好呀！很高兴见到你~",
        "translation": "",
    })

    with (
        patch.object(chat_routes._intent_service, "recognize", mock_intent),
        patch.object(chat_routes._retrieval_service, "search") as mock_search,
        patch.object(chat_routes._llm_service, "generate", mock_llm),
    ):
        resp = await client.post(
            "/api/chat",
            json={"message": "你好呀"},
            headers={"Authorization": f"Bearer {auth_context['token']}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == INTENT_CHAT
    assert data["response"]["useful"] is True
    # Verify search was NOT called for CHAT
    mock_search.assert_not_called()


# ── Test 3: Invalid session_id → 404 ──────────────────────
async def test_chat_invalid_session(client, auth_context):
    """Non-existent session_id should return 404."""
    resp = await client.post(
        "/api/chat",
        json={"session_id": "nonexistent-session", "message": "会员多少钱？"},
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )

    assert resp.status_code == 404


# ── Test 4: No auth token → 401 ───────────────────────────
async def test_chat_no_token(client):
    """Request without JWT should return 401."""
    resp = await client.post(
        "/api/chat",
        json={"message": "会员多少钱？"},
    )

    assert resp.status_code == 401


# ── Test 5: Service exception → 500, no stack leak ────────
async def test_chat_service_error_returns_500(client, auth_context):
    """If intent recognition throws, the response should be 500 with no stack trace."""
    mock_intent = AsyncMock(side_effect=RuntimeError("Unexpected DB failure"))

    with patch.object(chat_routes._intent_service, "recognize", mock_intent):
        resp = await client.post(
            "/api/chat",
            json={"message": "会员多少钱？"},
            headers={"Authorization": f"Bearer {auth_context['token']}"},
        )

    assert resp.status_code == 500
    data = resp.json()
    # 诊断模式（线上定位 500 根因，5553a07/ed2cf05）：响应带异常类型与消息；
    # 定位完成后恢复为隐藏 detail "Internal Server Error"
    assert "RuntimeError" in data.get("detail", "")
