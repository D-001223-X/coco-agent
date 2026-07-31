"""Dashboard admin service: aggregate metrics from the logs table."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Log

logger = logging.getLogger(__name__)


def _parse_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


class DashboardService:
    """Read-only analytics over the Log table."""

    async def get_dashboard(self, db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # ── All logs (recent 30 days) ─────────────────────
        cutoff = now - timedelta(days=30)
        result = await db.execute(
            select(Log).where(Log.created_at >= cutoff).order_by(Log.created_at.asc())
        )
        logs = result.scalars().all()

        # ── Aggregate per trace_id ────────────────────────
        traces: dict[str, dict] = {}
        for log in logs:
            tid = log.trace_id
            node = log.node
            created = log.created_at
            # SQLite returns naive datetimes; assume UTC for comparison
            if created is not None and created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            entry = traces.setdefault(
                tid,
                {
                    "intent": None,
                    "useful": None,
                    "llm_ms": 0,
                    "created_at": created,
                },
            )
            out = _parse_json(log.output_data)
            if node == "intent_recognition":
                entry["intent"] = out.get("intent")
            elif node == "llm_generate" or node == "llm_generation":
                entry["useful"] = out.get("useful")
                entry["llm_ms"] = log.duration_ms or 0

        total = len(traces)
        today_count = sum(
            1 for t in traces.values()
            if t["created_at"] and t["created_at"] >= today_start
        )
        refusal_count = sum(
            1 for t in traces.values() if t["useful"] is False
        )
        refusal_rate = round(refusal_count / total * 100, 1) if total else 0.0
        avg_ms = (
            round(sum(t["llm_ms"] for t in traces.values()) / total)
            if total
            else 0
        )

        # ── Intent distribution ───────────────────────────
        intent_dist: dict[str, int] = {}
        for t in traces.values():
            intent = t["intent"] or "UNKNOWN"
            intent_dist[intent] = intent_dist.get(intent, 0) + 1

        # ── 7-day refusal-rate trend ──────────────────────
        trends: list[dict] = []
        for i in range(6, -1, -1):
            day_start = (now - timedelta(days=i)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            day_end = day_start + timedelta(days=1)
            day_traces = [
                t for t in traces.values()
                if t["created_at"] and day_start <= t["created_at"] < day_end
            ]
            day_total = len(day_traces)
            day_refusal = sum(1 for t in day_traces if t["useful"] is False)
            trends.append({
                "date": day_start.strftime("%m-%d"),
                "requests": day_total,
                "refusal_rate": round(day_refusal / day_total * 100, 1) if day_total else 0.0,
            })

        return {
            "metrics": {
                "today_requests": today_count,
                "refusal_rate": refusal_rate,
                "avg_response_ms": avg_ms,
                "total_logs": total,
                "refusal_count": refusal_count,
            },
            "trends": trends,
            "intent_distribution": intent_dist,
        }
