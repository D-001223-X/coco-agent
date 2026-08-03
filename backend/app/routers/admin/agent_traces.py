"""Agent 决策轨迹查询 API（T-007）。

从 logs 表查询 Agent 相关节点（agent_decision / react_loop）的轨迹：
  GET /api/admin/agent/traces             — 轨迹列表（按 trace 聚合）
  GET /api/admin/agent/traces/{trace_id}  — 单个轨迹详情
"""

from __future__ import annotations

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Log, User
from app.routers.admin.deps import admin_read_guest_ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/agent", tags=["admin-agent"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(admin_read_guest_ok)]

_AGENT_NODES = ("agent_decision", "react_loop")


def _parse(data: str | None) -> dict:
    if not data:
        return {}
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {"raw": data}


@router.get("/traces")
async def get_agent_traces(
    _admin: AdminDep,
    db: DbDep,
    limit: int = 50,
    offset: int = 0,
):
    """返回 Agent 决策轨迹列表（按 trace_id 聚合，仅含 Agent 节点）。"""
    try:
        # 找出含 Agent 节点的 trace_id
        subq = (
            select(Log.trace_id)
            .where(Log.node.in_(_AGENT_NODES))
            .group_by(Log.trace_id)
            .order_by(func.max(Log.id).desc())
            .limit(limit)
            .offset(offset)
        )
        trace_ids = [r[0] for r in (await db.execute(subq)).fetchall()]
        if not trace_ids:
            return {"code": 0, "data": {"traces": [], "total": 0}, "msg": "success"}

        logs = (
            await db.execute(
                select(Log)
                .where(Log.trace_id.in_(trace_ids))
                .order_by(Log.id)
            )
        ).scalars().all()

        # 按 trace 聚合
        grouped: dict[str, list[Log]] = {}
        for lg in logs:
            grouped.setdefault(lg.trace_id, []).append(lg)

        traces = []
        for tid in trace_ids:
            nodes = grouped.get(tid, [])
            if not nodes:
                continue
            query = ""
            decision_path: list[str] = []
            total_ms = 0
            status = "success"
            for n in nodes:
                total_ms += n.duration_ms or 0
                decision_path.append(n.node)
                if n.status != "ok":
                    status = n.status
                inp = _parse(n.input_data)
                if not query and inp.get("query"):
                    query = inp["query"]
            session_id = next((n.session_id for n in nodes if n.session_id), None)
            user_id = next((n.user_id for n in nodes if n.user_id), None)
            traces.append({
                "trace_id": tid,
                "user_id": user_id,
                "session_id": session_id,
                "query": query or tid,
                "mode": next((_parse(n.input_data).get("mode") for n in nodes if _parse(n.input_data).get("mode")), "practice"),
                "decision_path": decision_path,
                "status": status,
                "total_duration_ms": total_ms,
                "created_at": nodes[-1].created_at.isoformat() if nodes[-1].created_at else "",
            })

        total = len(trace_ids)
        return {"code": 0, "data": {"traces": traces, "total": total}, "msg": "success"}
    except Exception as exc:
        logger.error("get_agent_traces failed: %s", exc)
        return {"code": 500, "data": None, "msg": str(exc)}


@router.get("/traces/{trace_id}")
async def get_agent_trace_detail(trace_id: str, _admin: AdminDep, db: DbDep):
    """返回单个决策轨迹的完整节点。"""
    try:
        result = await db.execute(
            select(Log)
            .where(Log.trace_id == trace_id)
            .order_by(Log.id)
        )
        rows = result.scalars().all()
        if not rows:
            return {"code": 404, "data": None, "msg": "轨迹不存在"}

        decision_path = []
        for i, n in enumerate(rows):
            decision_path.append({
                "node": n.node,
                "input": _parse(n.input_data),
                "output": _parse(n.output_data),
                "duration_ms": n.duration_ms or 0,
                "status": n.status,
                "order": i,
                "service": n.service,
            })

        query = next(
            (d["input"].get("query") for d in decision_path if d["input"].get("query")),
            trace_id,
        )
        return {
            "code": 0,
            "data": {
                "trace_id": trace_id,
                "query": query,
                "mode": next(
                    (d["input"].get("mode") for d in decision_path if d["input"].get("mode")),
                    "practice",
                ),
                "decision_path": decision_path,
                "status": "success" if all(d["status"] == "ok" for d in decision_path) else "failed",
                "total_duration_ms": sum(d["duration_ms"] for d in decision_path),
                "created_at": rows[-1].created_at.isoformat() if rows[-1].created_at else "",
            },
            "msg": "success",
        }
    except Exception as exc:
        logger.error("get_agent_trace_detail failed: %s", exc)
        return {"code": 500, "data": None, "msg": str(exc)}
