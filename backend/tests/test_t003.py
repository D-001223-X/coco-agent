"""T-003: Intent recognition service tests.

Covers 3 scenarios:
  1. "会员多少钱？" → SUPPORT
  2. "今天心情不好" → CHAT
  3. API timeout → graceful degradation to CHAT (no crash)
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import init_db
from app.services.intent_service import IntentResult, IntentService


# ── Fixture: temp DB so log_node has a target ─────────────
@pytest_asyncio.fixture
async def setup_db(tmp_path):
    """Initialise a temp SQLite DB so log_node can write without crashing."""
    db_path = tmp_path / "test_t003.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await init_db(database_url=db_url)

    # Patch the global session factory so log_node writes to our temp DB
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    from app.database import get_session_factory
    import app.database as db_module

    original_factory = db_module._session_factory
    db_module._session_factory = factory

    yield

    db_module._session_factory = original_factory
    await engine.dispose()


# ── Fixture: IntentService instance ───────────────────────
@pytest.fixture
def service():
    return IntentService()


# ── Helper: build a mock httpx.Response ────────────────────
def _mock_chat_response(content: str):
    """Build an object that behaves like the httpx response we use.

    httpx.Response.raise_for_status() and .json() are synchronous,
    so we use MagicMock (not AsyncMock) for the response object.
    """
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}}]
    }
    return mock_resp


# ── Test 1: "会员多少钱？" → SUPPORT ─────────────────────
async def test_recognize_support(service, setup_db):
    """A product pricing question should be classified as SUPPORT."""
    mock_content = json.dumps({
        "intent": "SUPPORT",
        "confidence": 0.95,
        "resolved_question": "会员多少钱？",
        "reason": "用户在询问会员价格，属于产品支持类咨询",
    })
    mock_resp = _mock_chat_response(mock_content)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await service.recognize("会员多少钱？", history=[])

    assert isinstance(result, IntentResult)
    assert result.intent == "SUPPORT"
    assert result.confidence > 0.5
    assert "会员" in result.resolved_question


# ── Test 2: "今天心情不好" → CHAT ─────────────────────────
async def test_recognize_chat(service, setup_db):
    """An emotional message with no product context should be CHAT."""
    mock_content = json.dumps({
        "intent": "CHAT",
        "confidence": 0.55,
        "resolved_question": "今天心情不好",
        "reason": "用户表达情绪状态，与产品无关，属于闲聊",
    })
    mock_resp = _mock_chat_response(mock_content)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await service.recognize("今天心情不好", history=[])

    assert isinstance(result, IntentResult)
    assert result.intent == "CHAT"
    assert result.resolved_question == "今天心情不好"


# ── Test 3: API timeout → degrade to CHAT ─────────────────
async def test_recognize_degrade_on_timeout(service, setup_db):
    """If the DeepSeek call times out, the service must NOT crash.

    It should return CHAT with confidence 0.0 and resolved_question
    equal to the original query.
    """
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=TimeoutError("Connection timed out"),
    ):
        result = await service.recognize("会员多少钱？", history=[])

    assert isinstance(result, IntentResult)
    assert result.intent == "CHAT"
    assert result.confidence == 0.0
    assert result.resolved_question == "会员多少钱？"
    assert "Degrade" in result.reason or "timed out" in result.reason.lower()
