"""Log query service — encapsulates trace summary and detail queries.

Keeps SQLAlchemy aggregation logic out of the router layer.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Log


class LogService:
    """Read-only log queries for the logs router."""

    @staticmethod
    async def list_traces(db: AsyncSession) -> list[dict]:
        """Return one summary row per trace_id, newest first.

        Each entry contains:
          - id: latest log's pk
          - trace_id
          - user_id
          - question: extracted from the first ``intent_recognition`` node's input_data
          - intent: inferred from the ``intent_recognition`` node's output_data
          - created_at: latest log's timestamp
        """
        # Subquery: latest id (pk) per trace_id
        latest_per_trace = (
            select(
                Log.trace_id,
                func.max(Log.id).label("max_id"),
            )
            .group_by(Log.trace_id)
            .subquery()
        )

        # Join back to get the full row with the latest id
        stmt = (
            select(Log)
            .join(
                latest_per_trace,
                (Log.trace_id == latest_per_trace.c.trace_id)
                & (Log.id == latest_per_trace.c.max_id),
            )
            .order_by(Log.id.desc())
        )

        result = await db.execute(stmt)
        latest_rows = result.scalars().all()

        # For each trace_id, also fetch the intent_recognition node for question/intent
        trace_ids = [row.trace_id for row in latest_rows]
        intent_logs = {}
        if trace_ids:
            intent_result = await db.execute(
                select(Log)
                .where(Log.trace_id.in_(trace_ids), Log.node == "intent_recognition")
                .order_by(Log.created_at.asc())
            )
            for log in intent_result.scalars().all():
                if log.trace_id not in intent_logs:
                    intent_logs[log.trace_id] = log

        output = []
        for row in latest_rows:
            intent_log = intent_logs.get(row.trace_id)

            # Extract question from intent_recognition input_data
            question = ""
            intent = ""
            if intent_log and intent_log.input_data:
                try:
                    input_data = json.loads(intent_log.input_data)
                    question = input_data.get("query", "")
                except (json.JSONDecodeError, TypeError):
                    question = intent_log.input_data[:100] if intent_log.input_data else ""
            else:
                # Fallback: extract from the latest log's input_data
                try:
                    inp = json.loads(row.input_data) if row.input_data else {}
                    question = inp.get("query", "")
                    if not question:
                        question = inp.get("message_preview", "")
                except (json.JSONDecodeError, TypeError):
                    question = str(row.input_data or "")[:100]

            # Extract intent from intent_recognition output_data
            if intent_log and intent_log.output_data:
                try:
                    out = json.loads(intent_log.output_data)
                    intent = out.get("intent", "")
                except (json.JSONDecodeError, TypeError):
                    pass

            output.append({
                "id": row.id,
                "trace_id": row.trace_id,
                "user_id": row.user_id,
                "question": question,
                "intent": intent,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            })

        return output

    @staticmethod
    async def get_trace_detail(
        db: AsyncSession,
        trace_id: str,
    ) -> dict[str, Any]:
        """Return full chain detail for a *trace_id*.

        Returns ``{"trace_id": ..., "user_id": ..., "nodes": [...]}``.
        """
        stmt = (
            select(Log)
            .where(Log.trace_id == trace_id)
            .order_by(Log.created_at.asc())
        )
        result = await db.execute(stmt)
        logs = result.scalars().all()

        user_id: int | None = None
        nodes: list[dict] = []

        for log in logs:
            if user_id is None and log.user_id is not None:
                user_id = log.user_id

            input_data: Any = log.input_data
            try:
                if input_data:
                    input_data = json.loads(input_data)
            except (json.JSONDecodeError, TypeError):
                pass

            output_data: Any = log.output_data
            try:
                if output_data:
                    output_data = json.loads(output_data)
            except (json.JSONDecodeError, TypeError):
                pass

            nodes.append({
                "node": log.node,
                "input_data": input_data,
                "output_data": output_data,
                "duration_ms": log.duration_ms,
                "service": log.service,
                "status": log.status,
            })

        return {
            "trace_id": trace_id,
            "user_id": user_id,
            "nodes": nodes,
        }
