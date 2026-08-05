"""T-009: Log query tests.

Covers 4 scenarios:
  1. List traces: insert 4 nodes → list returns 1 trace with correct question
  2. Trace detail: query by trace_id → returns 4 nodes in chronological order
  3. Non-existent trace_id → nodes: [], no error
  4. No auth token → 401
"""

import json
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import ADMIN_EMAIL, get_db, init_db
from app.main import app
from app.models import Log


# ── Fixture: test DB + auth token ────────────────────────
@pytest_asyncio.fixture
async def auth_context(tmp_path):
    """Seed temp DB, insert log nodes, return JWT."""
    db_path = tmp_path / "test_t009.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await init_db(database_url=db_url)

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    import app.database as db_module
    db_module._session_factory = factory

    trace_id = "trace-test-001"

    # Insert 4 log nodes simulating a full chat pipeline
    async with factory() as session:
        # Node 1: intent_recognition
        session.add(Log(
            trace_id=trace_id,
            node="intent_recognition",
            input_data=json.dumps({"query": "会员多少钱？", "history": []}),
            output_data=json.dumps({
                "intent": "SUPPORT",
                "confidence": 0.95,
                "resolved_question": "会员多少钱？",
                "reason": "产品价格咨询",
            }),
            duration_ms=200,
            service="DeepSeek",
            status="ok",
            user_id=1,
            session_id="sess-1",
        ))
        # Node 2: retrieval
        session.add(Log(
            trace_id=trace_id,
            node="retrieval",
            input_data=json.dumps({"query": "会员多少钱？", "top_k": 3, "threshold": 0.3}),
            output_data=json.dumps({"count": 2, "top_scores": [0.9, 0.7]}),
            duration_ms=50,
            service="FAISS+FTS5+RRF",
            status="ok",
            user_id=1,
        ))
        # Node 3: rerank
        session.add(Log(
            trace_id=trace_id,
            node="rerank",
            input_data=json.dumps({"query": "会员多少钱？", "document_count": 2, "top_k": 3}),
            output_data=json.dumps({"result_count": 2}),
            duration_ms=30,
            service="qwen3-rerank",
            status="ok",
            user_id=1,
        ))
        # Node 4: llm_generate
        session.add(Log(
            trace_id=trace_id,
            node="llm_generate",
            input_data=json.dumps({"query": "会员多少钱？", "intent": "SUPPORT", "chunk_count": 2}),
            output_data=json.dumps({"useful": True, "content_preview": "可可语伴会员每月68元"}),
            duration_ms=800,
            service="DeepSeek",
            status="ok",
            user_id=1,
        ))
        await session.commit()

    # Generate JWT
    from app.routers.auth import create_access_token
    token = create_access_token(
        data={"sub": ADMIN_EMAIL, "role": "admin", "user_id": 1}
    )

    yield {
        "token": token,
        "trace_id": trace_id,
        "factory": factory,
        "engine": engine,
    }

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(auth_context):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Test 1: List traces → returns summary with question ────
async def test_list_logs(client, auth_context):
    """List should return 1 trace with correct question and intent."""
    resp = await client.get(
        "/api/logs",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["logs"]) == 1

    entry = data["logs"][0]
    assert entry["trace_id"] == auth_context["trace_id"]
    assert entry["question"] == "会员多少钱？"
    assert entry["intent"] == "SUPPORT"
    assert entry["user_id"] == 1
    assert entry["created_at"] is not None

    # Verify full input_data is NOT in the list response
    assert "input_data" not in entry
    assert "output_data" not in entry


# ── Test 2: Trace detail → 4 nodes in chronological order ──
async def test_get_trace_detail(client, auth_context):
    """Detail should return 4 nodes ordered by time."""
    resp = await client.get(
        f"/api/logs/{auth_context['trace_id']}",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == auth_context["trace_id"]
    assert data["user_id"] == 1
    assert len(data["nodes"]) == 4

    # Chronological order: intent → retrieval → rerank → llm
    expected_nodes = ["intent_recognition", "retrieval", "rerank", "llm_generate"]
    actual_nodes = [n["node"] for n in data["nodes"]]
    assert actual_nodes == expected_nodes, f"Expected {expected_nodes}, got {actual_nodes}"

    # Each node has the required fields
    for node in data["nodes"]:
        assert "input_data" in node
        assert "output_data" in node
        assert node["duration_ms"] is not None
        assert node["service"] != ""
        assert node["status"] != ""


# ── Test 3: Non-existent trace_id → nodes: [] ──────────────
async def test_get_trace_not_found(client, auth_context):
    """Non-existent trace_id should return empty nodes, no error."""
    resp = await client.get(
        "/api/logs/nonexistent-trace",
        headers={"Authorization": f"Bearer {auth_context['token']}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["trace_id"] == "nonexistent-trace"
    assert data["user_id"] is None
    assert data["nodes"] == []


# ── Test 4: No auth token → 200 空列表（R-003 访客无身份时返回空）──
async def test_logs_no_token(client):
    """无 token 无 device → 200 + 空列表（不再 401）。"""
    resp = await client.get("/api/logs")
    assert resp.status_code == 200
    assert resp.json()["logs"] == []

    resp = await client.get("/api/logs/some-trace")
    assert resp.status_code == 200
    assert resp.json()["nodes"] == []
