"""Full-chain async logging utility.

Design principles:
  • Non-blocking: uses ``asyncio.create_task`` — never ``await`` the DB write.
  • Fail-silent: if the write fails, print a warning to stderr and move on.
  • Isolated: imports the session factory lazily to avoid circular imports.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


async def _write_log(
    session_factory: async_sessionmaker[AsyncSession],
    trace_id: str,
    node: str,
    input_data: Any,
    output_data: Any,
    duration_ms: int,
    service: str,
    status: str,
    user_id: int | None,
    session_id: str | None,
) -> None:
    """Internal coroutine: opens a session and inserts the log row.

    Runs inside ``asyncio.create_task`` so callers never block on it.
    """
    input_str = (
        input_data
        if isinstance(input_data, str)
        else json.dumps(input_data, ensure_ascii=False, default=str)
    )
    output_str = (
        output_data
        if isinstance(output_data, str)
        else json.dumps(output_data, ensure_ascii=False, default=str)
    )

    sql = text(
        """
        INSERT INTO logs
            (trace_id, node, input_data, output_data,
             duration_ms, service, status, user_id, session_id)
        VALUES
            (:trace_id, :node, :input_data, :output_data,
             :duration_ms, :service, :status, :user_id, :session_id)
        """
    )

    async with session_factory() as session:
        await session.execute(
            sql,
            {
                "trace_id": trace_id,
                "node": node,
                "input_data": input_str,
                "output_data": output_str,
                "duration_ms": duration_ms,
                "service": service,
                "status": status,
                "user_id": user_id,
                "session_id": session_id,
            },
        )
        await session.commit()


def log_node(
    trace_id: str,
    node: str,
    input_data: Any,
    output_data: Any,
    duration_ms: int,
    service: str,
    status: str = "ok",
    user_id: int | None = None,
    session_id: str | None = None,
) -> asyncio.Task:
    """Fire-and-forget async log writer.

    Schedules the DB write as an ``asyncio.Task`` and returns the task
    handle immediately without awaiting it.  If the write fails, the
    exception is caught in the done-callback and only a warning is
    printed to stderr — the main business flow is never interrupted.

    Parameters
    ----------
    trace_id : str
        Unique request/trace identifier.
    node : str
        Pipeline node name (e.g. ``"retriever"``, ``"reranker"``, ``"llm"``).
    input_data : Any
        Serialisable input payload (dict / str / None).
    output_data : Any
        Serialisable output payload.
    duration_ms : int
        Elapsed wall-clock time of the node in milliseconds.
    service : str
        Name of the service that produced this log entry.
    status : str
        ``"ok"`` / ``"error"`` / custom.
    user_id : int | None
        Associated user ID (nullable).
    session_id : str | None
        Associated session ID (nullable).

    Returns
    -------
    asyncio.Task
        The background task handle.  Callers *may* await it in tests
        but are not required to in production code.
    """
    # Lazy import to avoid circular dependency at module load time
    from app.database import get_session_factory

    session_factory = get_session_factory()

    task = asyncio.create_task(
        _write_log(
            session_factory,
            trace_id=trace_id,
            node=node,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            service=service,
            status=status,
            user_id=user_id,
            session_id=session_id,
        )
    )

    # Fail-silent: catch any exception, print warning, never raise.
    def _on_done(t: asyncio.Task) -> None:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            print(
                f"[logger] WARNING: log write failed for "
                f"trace_id={trace_id} node={node}: {exc}",
                file=sys.stderr,
            )

    task.add_done_callback(_on_done)
    return task
