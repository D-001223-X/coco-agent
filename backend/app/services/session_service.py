"""Session service — encapsulates session-list and message-queries.

Keeps ORM query logic out of the router layer.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Session


class SessionService:
    """Read-only session and message queries for the sessions router."""

    @staticmethod
    async def list_user_sessions(
        db: AsyncSession,
        user_id: int,
    ) -> list[dict]:
        """Return all sessions belonging to *user_id*, ordered by updated_at desc.

        Each entry includes ``session_id``, ``created_at``, ``updated_at``,
        and ``message_count``.
        """
        # Subquery: message count per session
        count_subq = (
            select(
                Message.session_id,
                func.count(Message.id).label("msg_count"),
            )
            .group_by(Message.session_id)
            .subquery()
        )

        stmt = (
            select(
                Session.id,
                Session.created_at,
                Session.updated_at,
                func.coalesce(count_subq.c.msg_count, 0).label("message_count"),
            )
            .outerjoin(count_subq, Session.id == count_subq.c.session_id)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
        )

        result = await db.execute(stmt)
        rows = result.all()

        return [
            {
                "session_id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "message_count": row.message_count,
            }
            for row in rows
        ]

    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 50,
        before: int | None = None,
    ) -> list[dict]:
        """Return messages for *session_id* with cursor-based pagination.

        If *before* is None, returns the latest *limit* messages.
        If *before* is set, returns *limit* messages with ``id < before``.
        Results are sorted by ``created_at`` ascending.
        """
        query = (
            select(Message.id, Message.role, Message.content, Message.created_at)
            .where(Message.session_id == session_id)
        )

        if before is not None:
            query = query.where(Message.id < before)

        # Fetch latest messages, then reverse for chronological order
        query = query.order_by(Message.id.desc()).limit(limit)

        result = await db.execute(query)
        rows = result.all()

        # Reverse so oldest is first
        rows = list(reversed(rows))

        return [
            {
                "id": row.id,
                "role": row.role,
                "content": row.content,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    @staticmethod
    async def validate_session_owner(
        db: AsyncSession,
        session_id: str,
        user_id: int,
    ) -> Session | None:
        """Return the Session if it exists and belongs to *user_id*, else None."""
        stmt = select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
