"""Tests for app.database.init_db — ORM + FTS5 + admin seeding + idempotency."""

import os
import tempfile

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import ADMIN_EMAIL, init_db
from app.models import Base, User


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────
@pytest.fixture
def file_db_url(tmp_path) -> str:
    """Use a temp file-based DB so data persists across connections."""
    db_path = str(tmp_path / "test_coco.db")
    return f"sqlite+aiosqlite:///{db_path}"


@pytest_asyncio.fixture
async def initialised_engine(file_db_url):
    """Run init_db on a temp file DB and return the engine for queries."""
    await init_db(database_url=file_db_url)
    engine = create_async_engine(file_db_url, echo=False)
    yield engine
    await engine.dispose()


# ──────────────────────────────────────────────────────────────
# Normal: FTS5 table exists and admin row present after init_db
# ──────────────────────────────────────────────────────────────
async def test_init_db_creates_fts_and_admin(initialised_engine):
    """After init_db:
      • sqlite_master contains 'knowledge_fts'
      • users table has admin@app.com
    """
    session_factory = async_sessionmaker(
        initialised_engine, expire_on_commit=False
    )
    async with session_factory() as session:
        # ── Check FTS5 virtual table ────────────────────────
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        table_names = {row[0] for row in result.fetchall()}
        assert "knowledge_fts" in table_names, (
            f"knowledge_fts not found in {table_names}"
        )

        # ── Check admin user ────────────────────────────────
        result = await session.execute(
            text("SELECT email, role FROM users WHERE email = :email"),
            {"email": ADMIN_EMAIL},
        )
        row = result.fetchone()
        assert row is not None, "admin@app.com not found in users table"
        assert row[0] == ADMIN_EMAIL
        assert row[1] == "admin"


# ──────────────────────────────────────────────────────────────
# Boundary: calling init_db twice does not raise / duplicate admin
# ──────────────────────────────────────────────────────────────
async def test_init_db_idempotent(file_db_url):
    """init_db() should be safe to call twice — no error, no duplicate admin."""

    # First init
    await init_db(database_url=file_db_url)

    # Second init — must not raise
    await init_db(database_url=file_db_url)

    # Verify only one admin row
    engine = create_async_engine(file_db_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": ADMIN_EMAIL},
        )
        count = result.scalar()
        assert count == 1, f"Expected 1 admin row, got {count}"

    await engine.dispose()


# ──────────────────────────────────────────────────────────────
# Normal: admin password is bcrypt-hashed (not plaintext)
# ──────────────────────────────────────────────────────────────
async def test_init_db_admin_password_is_bcrypt(initialised_engine):
    """The admin's stored password should be a bcrypt hash, not '123456'."""
    session_factory = async_sessionmaker(initialised_engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT hashed_password FROM users WHERE email = :email"),
            {"email": ADMIN_EMAIL},
        )
        hashed = result.scalar()
        assert hashed is not None
        assert hashed != "123456", "Password stored as plaintext!"
        assert hashed.startswith("$2"), f"Not a bcrypt hash: {hashed[:20]}..."

        # Verify it matches
        from app.database import verify_password

        assert verify_password("123456", hashed)
