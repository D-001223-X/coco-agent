"""Async database engine, session factory, and initialisation logic.

Ensures:
  • ORM tables created via SQLAlchemy ``create_all``.
  • FTS5 virtual table ``knowledge_fts`` created via raw SQL (SQLite only).
  • Default admin account inserted (bcrypt-hashed, idempotent).

Database backends:
  • SQLite (local dev / tests): aiosqlite + FTS5 full-text index.
  • MySQL / CloudBase 云数据库 (production): aiomysql, no FTS5 —
    retrieval falls back to FAISS vectors + Python keyword matching.
"""

from __future__ import annotations

import logging
from typing import Any

import bcrypt
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Base, User

logger = logging.getLogger(__name__)

# ── Password hashing (bcrypt direct, no passlib) ──────────
def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check *plain* against a previously generated bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

ADMIN_EMAIL = "admin@app.com"
ADMIN_PASSWORD = "123456"
ADMIN_ROLE = "admin"


# ── Engine / session factory ──────────────────────────────
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        url = get_settings().effective_database_url
        kwargs: dict[str, Any] = {"echo": False}
        # MySQL/CloudBase 云数据库：连接池 + utf8mb4 + 短超时（CloudBase 网关 30s）
        if url.startswith("mysql"):
            kwargs.update({
                "pool_size": 5,
                "max_overflow": 10,
                "pool_recycle": 3600,
                "pool_pre_ping": True,   # 借用前 ping 检测死连接，避免挂起
                # aiomysql 通过 connect_args 传连接超时（秒）
                "connect_args": {"connect_timeout": 10},
            })
        _engine = create_async_engine(url, **kwargs)
    return _engine


def is_sqlite_url(url: str) -> bool:
    """判断是否 SQLite（决定是否创建 FTS5 虚拟表）。"""
    return url.startswith("sqlite")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields an async session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


# ── FTS5 DDL ──────────────────────────────────────────────
_FTS5_SQL = text("""
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
USING fts5(
    title,
    content,
    chunk_id      UNINDEXED,
    tokenize = 'unicode61'
);
""")


# ── Init ───────────────────────────────────────────────────
async def init_db(database_url: str | None = None) -> None:
    """Initialise the database.

    1.  Create all ORM tables (``create_all``).
    2.  Create the FTS5 virtual table ``knowledge_fts``.
    3.  Insert the default admin account if not present.

    The function is **idempotent**: running it multiple times will
    not raise errors or duplicate the admin row.
    """
    if database_url:
        engine = create_async_engine(database_url, echo=False)
    else:
        engine = get_engine()

    is_sqlite = is_sqlite_url(database_url or get_settings().effective_database_url)

    # ── 1. ORM tables ──────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # ── 1b. 增量迁移：给旧表补列（create_all 不会改已存在的表）──
        # P-002: sessions.device_id（访客设备标识）
        if not is_sqlite:
            try:
                # MySQL: 检查列是否存在，不存在则 ALTER 添加
                insp = await conn.run_sync(
                    lambda sync_conn: inspect(sync_conn).get_columns("sessions")
                )
                has_device = any(c["name"] == "device_id" for c in insp)
                if not has_device:
                    await conn.execute(
                        text("ALTER TABLE sessions ADD COLUMN device_id VARCHAR(64) NULL")
                    )
                    logger.info("Migration: sessions.device_id added")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Migration sessions.device_id skipped: %s", exc)
        else:
            # SQLite: 简单检测 + ALTER（幂等）
            try:
                cols = await conn.execute(text("PRAGMA table_info(sessions)"))
                names = [r[1] for r in cols.fetchall()]
                if "device_id" not in names:
                    await conn.execute(
                        text("ALTER TABLE sessions ADD COLUMN device_id VARCHAR(64)")
                    )
                    logger.info("Migration: sessions.device_id added (sqlite)")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Migration sessions.device_id skipped: %s", exc)

        # ── 2. FTS5 virtual table（仅 SQLite）───────────────
        # MySQL/CloudBase 云数据库无 FTS5：跳过，检索走 FAISS 向量 + Python 关键词。
        if is_sqlite:
            await conn.execute(_FTS5_SQL)

    # ── 3. Default admin ──────────────────────────────────
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        # Check if admin already exists (idempotency)
        stmt = User.__table__.select().where(User.email == ADMIN_EMAIL)
        result = await session.execute(stmt)
        existing = result.fetchone()

        if existing is None:
            admin = User(
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=ADMIN_ROLE,
            )
            session.add(admin)
            await session.commit()
            logger.info("Default admin account created: %s", ADMIN_EMAIL)
        else:
            logger.debug("Admin account already exists, skipping.")

    # If we created a throwaway engine, dispose it
    if database_url:
        await engine.dispose()


# ── Utility for tests ──────────────────────────────────────
async def init_db_with_url(database_url: str) -> None:
    """Convenience wrapper: init_db with an explicit database URL."""
    await init_db(database_url=database_url)
