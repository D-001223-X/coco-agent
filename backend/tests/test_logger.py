"""Tests for app.utils.logger.log_node — async fire-and-forget logging."""

import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import init_db
from app.utils.logger import log_node


# ──────────────────────────────────────────────────────────────
# Fixtures: set up an in-memory/file DB and wire the session factory
# ──────────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def db_env(monkeypatch):
    """Initialise a temp file-based DB and patch get_session_factory to use it."""
    import tempfile
    import os

    tmpdir = tempfile.mkdtemp()
    db_path = f"{tmpdir}/test_log.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    await init_db(database_url=db_url)

    engine = create_async_engine(db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Patch the factory used inside log_node
    import app.database as db_module

    original_get_factory = db_module.get_session_factory
    monkeypatch.setattr(db_module, "get_session_factory", lambda: session_factory)

    # Also patch logger module's lazy import path
    import app.utils.logger as logger_module

    async def mock_get_session_factory():
        return session_factory

    monkeypatch.setattr(
        db_module,
        "get_session_factory",
        lambda: session_factory,
    )

    yield {
        "engine": engine,
        "session_factory": session_factory,
        "db_url": db_url,
        "db_path": db_path,
        "tmpdir": tmpdir,
    }

    await engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)
    os.rmdir(tmpdir)


# ──────────────────────────────────────────────────────────────
# Normal: log_node writes a complete record
# ──────────────────────────────────────────────────────────────
async def test_log_node_writes_record(db_env):
    """Call log_node, wait 0.1s, then verify the log row in DB."""
    sf = db_env["session_factory"]

    task = log_node(
        trace_id="trace-001",
        node="retriever",
        input_data={"query": "可可语伴多少钱"},
        output_data={"answer": "68元/月"},
        duration_ms=42,
        service="rag",
        status="ok",
        user_id=1,
        session_id="sess-abc",
    )

    # Wait for the background task to complete
    await asyncio.sleep(0.3)

    # Verify the row
    async with sf() as session:
        result = await session.execute(
            text(
                "SELECT trace_id, node, input_data, output_data, "
                "duration_ms, service, status, user_id, session_id "
                "FROM logs WHERE trace_id = :tid"
            ),
            {"tid": "trace-001"},
        )
        row = result.fetchone()

    assert row is not None, "Log row not found"
    assert row[0] == "trace-001"
    assert row[1] == "retriever"
    assert "可可语伴多少钱" in row[2]
    assert "68元/月" in row[3]
    assert row[4] == 42
    assert row[5] == "rag"
    assert row[6] == "ok"
    assert row[7] == 1
    assert row[8] == "sess-abc"


# ──────────────────────────────────────────────────────────────
# Boundary: user_id and session_id are None → DB columns should be NULL
# ──────────────────────────────────────────────────────────────
async def test_log_node_none_ids(db_env):
    """log_node with user_id=None and session_id=None should store NULL."""
    sf = db_env["session_factory"]

    task = log_node(
        trace_id="trace-002",
        node="llm",
        input_data="hello",
        output_data="world",
        duration_ms=10,
        service="deepseek",
        status="ok",
        user_id=None,
        session_id=None,
    )

    await asyncio.sleep(0.3)

    async with sf() as session:
        result = await session.execute(
            text(
                "SELECT user_id, session_id FROM logs WHERE trace_id = :tid"
            ),
            {"tid": "trace-002"},
        )
        row = result.fetchone()

    assert row is not None
    assert row[0] is None, f"user_id should be NULL, got {row[0]}"
    assert row[1] is None, f"session_id should be NULL, got {row[1]}"


# ──────────────────────────────────────────────────────────────
# Edge: log_node does not block the caller (returns immediately)
# ──────────────────────────────────────────────────────────────
async def test_log_node_non_blocking(db_env):
    """log_node should return a Task without the caller awaiting it."""
    import time

    t0 = time.monotonic()
    task = log_node(
        trace_id="trace-003",
        node="reranker",
        input_data="x",
        output_data="y",
        duration_ms=5,
        service="qwen3-rerank",
        status="ok",
    )
    elapsed = time.monotonic() - t0

    # Should return near-instantly (< 0.05s) — it's a fire-and-forget Task
    assert elapsed < 0.5, f"log_node took {elapsed:.3f}s — seems blocking!"
    assert not task.done(), "Task should still be pending when returned"

    # Clean up
    await asyncio.sleep(0.3)
