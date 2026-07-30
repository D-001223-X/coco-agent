"""T-004: Hybrid retrieval service tests.

Covers 3 scenarios:
  1. Normal: "会员多少钱" returns chunks containing "68元"
  2. Boundary: "火星殖民" returns empty list
  3. Exception: missing FAISS index → empty list, no crash
"""

import json
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import init_db
from app.services.retrieval_service import RetrievedChunk, RetrievalService


# ── Fixture: temp DB with FTS5 populated + FAISS index ────
@pytest_asyncio.fixture
async def setup_db(tmp_path):
    """Init temp DB, seed FTS5, build FAISS index for the test."""
    from scripts.build_index import chunk_markdown, build_faiss_index, populate_fts5
    from pathlib import Path

    db_path = tmp_path / "test_t004.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    await init_db(database_url=db_url)

    # Read knowledge base and build artifacts
    kb_path = (
        Path(__file__).resolve().parent.parent.parent
        / "knowledge_base" / "coco_knowledge.md"
    )
    md_text = kb_path.read_text(encoding="utf-8")
    chunks = chunk_markdown(md_text)

    # Build FAISS index + chunks.json in tmp_path
    index, _ = build_faiss_index(chunks)
    import faiss
    faiss_path = tmp_path / "test_faiss.index"
    faiss.write_index(index, str(faiss_path))

    chunks_path = tmp_path / "test_chunks.json"
    chunks_path.write_text(
        json.dumps(chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Populate FTS5
    await populate_fts5(chunks, db_url)

    # Patch the global session factory so log_node writes to our temp DB
    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    import app.database as db_module
    original_factory = db_module._session_factory
    db_module._session_factory = factory

    yield {
        "db_url": db_url,
        "faiss_path": str(faiss_path),
        "chunks_path": str(chunks_path),
    }

    db_module._session_factory = original_factory
    await engine.dispose()


# ── Test 1: Normal search — "会员多少钱" contains "68元" ────
async def test_search_returns_pricing_info(setup_db):
    """Searching for '会员多少钱' should return chunks about pricing."""
    svc = RetrievalService()
    svc._settings.faiss_index_path = setup_db["faiss_path"]
    svc._settings.chunks_meta_path = setup_db["chunks_path"]

    results = await svc.search("会员多少钱", top_k=3, threshold=0.0)

    assert len(results) > 0
    all_content = " ".join(r.content for r in results)
    assert "68" in all_content, f"Expected '68' in results, got: {all_content[:200]}"
    assert all(isinstance(r, RetrievedChunk) for r in results)
    assert results[0].score >= results[-1].score


# ── Test 2: Boundary — "火星殖民" returns empty ─────────────
async def test_search_no_match_returns_empty(setup_db):
    """A query with no relevant content should return an empty list."""
    svc = RetrievalService()
    svc._settings.faiss_index_path = setup_db["faiss_path"]
    svc._settings.chunks_meta_path = setup_db["chunks_path"]

    results = await svc.search("火星殖民", top_k=3, threshold=0.5)

    assert results == [], f"Expected empty list, got {len(results)} results"


# ── Test 3: Exception — FAISS index missing → empty list ────
async def test_search_missing_index_no_crash(setup_db):
    """If the FAISS index file doesn't exist, search must not crash."""
    svc = RetrievalService()
    svc._settings.faiss_index_path = "/tmp/nonexistent_faiss.index"
    svc._settings.chunks_meta_path = "/tmp/nonexistent_chunks.json"

    results = await svc.search("会员多少钱", top_k=3, threshold=0.3)

    assert results == [], f"Expected empty list on missing index, got {results}"
