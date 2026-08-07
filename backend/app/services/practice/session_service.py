"""陪练会话业务逻辑（T-004）。

管理 Skill 实例、会话状态与 Agent 决策集成。

P0 根治（2026-08-07）：会话状态实时持久化到 ``practice_running_sessions`` 表。
CloudBase 无状态云函数多实例下，纯内存会话会跨实例丢失（start/chat 路由到
不同实例 → 404）。改造后：start 落库、chat/switch 按需从 DB 恢复并更新、
end 归档到 ``practice_session_records`` 并删除 running 行。
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from app.agent.decision_maker import DecisionMaker
from app.agent.skills import get_default_scenario, load_skill
from app.agent.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class PracticeSession:
    """单个陪练会话。"""

    def __init__(
        self,
        session_id: str,
        mode: str,
        scenario: str,
        user_level: str,
        user_id: str,
        skill: BaseSkill,
    ) -> None:
        self.session_id = session_id
        self.mode = mode
        self.scenario = scenario
        self.user_level = user_level
        self.user_id = user_id
        self.skill = skill
        self.history: list[dict[str, Any]] = []
        self.started_at = time.time()
        self.ended_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessionId": self.session_id,
            "mode": self.mode,
            "scenario": self.scenario,
            "userLevel": self.user_level,
            "userId": self.user_id,
            "rounds": self.history,
            "startedAt": self.started_at,
            "endedAt": self.ended_at,
        }


class SessionService:
    """会话管理：创建、对话、结束（内存缓存 + DB 持久化，多实例可靠）。"""

    def __init__(self) -> None:
        self._sessions: dict[str, PracticeSession] = {}
        self._decision_maker = DecisionMaker()

    # ── 生命周期 ─────────────────────────────────────────
    async def start_session(
        self, mode: str, scenario: str, user_level: str, user_id: str, db: Any = None
    ) -> tuple[PracticeSession, str]:
        """创建会话，返回 (session, greeting)。落库保证多实例可见。"""
        scenario = scenario or get_default_scenario(mode)
        skill = load_skill(mode, user_level, scenario)
        greeting = skill.get_greeting()

        session_id = f"session_{uuid.uuid4().hex[:10]}"
        session = PracticeSession(
            session_id=session_id,
            mode=mode,
            scenario=scenario,
            user_level=user_level,
            user_id=user_id,
            skill=skill,
        )
        session.history.append({
            "id": f"round_{uuid.uuid4().hex[:8]}",
            "role": "agent",
            "content": greeting,
            "correction": None,
            "agentThought": None,
            "timestamp": _now_iso(),
        })
        self._sessions[session_id] = session
        if db is not None:
            await self._save_running_async(session, db)
        return session, greeting

    async def get_session(
        self, session_id: str, db: Any = None
    ) -> PracticeSession | None:
        """内存优先；miss 且提供 db 时从 running 表恢复（多实例兜底）。"""
        session = self._sessions.get(session_id)
        if session is not None:
            return session
        if db is not None:
            session = await self._load_running_async(session_id, db)
            if session is not None:
                self._sessions[session_id] = session  # 放回本实例缓存
        return session

    def end_session(self, session_id: str) -> PracticeSession | None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            session.ended_at = time.time()
            # 持久化会话记录（T-006 进度统计）
            self._persist_session(session)
        return session

    async def end_session_async(
        self, session_id: str, db: Any = None
    ) -> PracticeSession | None:
        """结束会话并持久化（异步版本，支持传入 AsyncSession）。"""
        session = self._sessions.pop(session_id, None)
        if session is None and db is not None:
            session = await self._load_running_async(session_id, db)
        if session is not None:
            session.ended_at = time.time()
            if db is not None:
                await self._persist_session_async(session, db)
                await self._delete_running_async(session_id, db)
        return session

    def _persist_session(self, session: PracticeSession) -> None:
        """同步持久化（无 db 时打印日志，由异步版本负责真正入库）。"""
        logger.info(
            "[session] 会话结束待持久化: %s mode=%s rounds=%d",
            session.session_id, session.mode, len(session.history),
        )

    @staticmethod
    async def _persist_session_async(session: PracticeSession, db) -> None:
        """将会话记录写入数据库。"""
        from datetime import datetime, timezone

        from sqlalchemy import select

        from app.models import PracticeSessionRecord

        record = await db.execute(
            select(PracticeSessionRecord).where(
                PracticeSessionRecord.session_id == session.session_id
            )
        )
        existing = record.scalar_one_or_none()
        payload = json.dumps(session.history, ensure_ascii=False)
        if existing:
            existing.rounds_json = payload
            existing.ended_at = datetime.now(timezone.utc)
        else:
            db.add(PracticeSessionRecord(
                session_id=session.session_id,
                user_id=session.user_id,
                mode=session.mode,
                scenario=session.scenario,
                user_level=session.user_level,
                rounds_json=payload,
                started_at=datetime.fromtimestamp(
                    session.started_at, tz=timezone.utc
                ),
                ended_at=datetime.now(timezone.utc),
            ))
        await db.commit()

    # ── running 表持久化（P0 根治）────────────────────────
    @staticmethod
    async def _save_running_async(session: PracticeSession, db) -> None:
        """保存/更新进行中会话状态。"""
        from datetime import datetime, timezone

        from sqlalchemy import select

        from app.models import PracticeRunningSession

        row = await db.execute(
            select(PracticeRunningSession).where(
                PracticeRunningSession.session_id == session.session_id
            )
        )
        existing = row.scalar_one_or_none()
        if existing is None:
            db.add(PracticeRunningSession(
                session_id=session.session_id,
                user_id=session.user_id,
                mode=session.mode,
                scenario=session.scenario,
                user_level=session.user_level,
                history_json=json.dumps(session.history, ensure_ascii=False),
                skill_history_json=json.dumps(
                    session.skill.conversation_history, ensure_ascii=False
                ),
                started_at=datetime.fromtimestamp(
                    session.started_at, tz=timezone.utc
                ),
            ))
        else:
            existing.scenario = session.scenario
            existing.history_json = json.dumps(session.history, ensure_ascii=False)
            existing.skill_history_json = json.dumps(
                session.skill.conversation_history, ensure_ascii=False
            )
        await db.commit()

    @staticmethod
    async def _load_running_async(
        session_id: str, db
    ) -> PracticeSession | None:
        """从 running 表恢复会话（重建 skill 并恢复对话历史）。"""
        from datetime import timezone

        from sqlalchemy import select

        from app.models import PracticeRunningSession

        row = await db.execute(
            select(PracticeRunningSession).where(
                PracticeRunningSession.session_id == session_id
            )
        )
        rec = row.scalar_one_or_none()
        if rec is None:
            return None
        try:
            skill = load_skill(rec.mode, rec.user_level, rec.scenario)
            skill.conversation_history = json.loads(rec.skill_history_json or "[]")
            session = PracticeSession(
                session_id=rec.session_id,
                mode=rec.mode,
                scenario=rec.scenario,
                user_level=rec.user_level,
                user_id=rec.user_id,
                skill=skill,
            )
            session.history = json.loads(rec.history_json or "[]")
            session.started_at = rec.started_at.replace(
                tzinfo=timezone.utc
            ).timestamp()
            return session
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "恢复会话 %s 失败: %s（忽略，视为会话不存在）", session_id, exc
            )
            return None

    @staticmethod
    async def _delete_running_async(session_id: str, db) -> None:
        from sqlalchemy import delete

        from app.models import PracticeRunningSession

        await db.execute(
            delete(PracticeRunningSession).where(
                PracticeRunningSession.session_id == session_id
            )
        )
        await db.commit()

    async def switch_scenario(
        self, session_id: str, scenario: str, db: Any = None
    ) -> tuple[PracticeSession, str]:
        """切换会话的场景/话题，保留对话历史（T-005）。

        Returns
        -------
        (session, new_greeting)
        """
        session = await self.get_session(session_id, db)
        if session is None:
            raise KeyError(f"会话不存在: {session_id}")

        # Skill 切换场景（保留 conversation_history）
        session.skill.switch_context(scenario)
        session.scenario = scenario
        new_greeting = session.skill.get_greeting()

        # 记录一条系统消息表明场景已切换
        session.history.append({
            "id": f"round_{uuid.uuid4().hex[:8]}",
            "role": "agent",
            "content": f"🔀 场景已切换：{new_greeting}",
            "correction": None,
            "agentThought": "场景/话题动态切换，历史上下文已保留",
            "timestamp": _now_iso(),
        })
        if db is not None:
            await self._save_running_async(session, db)
        return session, new_greeting

    # ── 对话 ─────────────────────────────────────────────
    async def chat(self, session_id: str, message: str, db: Any = None) -> dict[str, Any]:
        """处理用户消息，返回 Agent 回复 + 纠错 + 决策轨迹。每轮落库。"""
        import time as _time

        from app.utils.logger import log_node

        session = await self.get_session(session_id, db)
        if session is None:
            raise KeyError(f"会话不存在: {session_id}")

        trace_id = f"agent_{session_id}_{uuid.uuid4().hex[:8]}"

        # Agent 决策层集成：判断走直接回复（SIMPLE_ANSWER）还是深度处理
        t0 = _time.perf_counter()
        decision = await self._decision_maker.decide(
            query=message,
            intent="PRACTICE",
            confidence=0.9,  # 陪练场景置信度固定偏高（消息都是练习输入）
            context="口语陪练",
        )
        log_node(
            trace_id=trace_id,
            node="agent_decision",
            input_data={"query": message, "mode": session.mode, "scenario": session.scenario},
            output_data={
                "decision": decision.decision.value,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "fallback_to_workflow": decision.fallback_to_workflow,
            },
            duration_ms=int((_time.perf_counter() - t0) * 1000),
            service="DecisionMaker",
            user_id=int(session.user_id) if str(session.user_id).isdigit() else None,
            session_id=session_id,
        )

        # 记录用户消息
        session.history.append({
            "id": f"round_{uuid.uuid4().hex[:8]}",
            "role": "user",
            "content": message,
            "correction": None,
            "agentThought": None,
            "timestamp": _now_iso(),
        })
        session.skill.append_history("user", message)

        # Skill 处理（ReAct 决策轨迹：skill 即 Agent 执行层）
        t1 = _time.perf_counter()
        result = await session.skill.process_user_input(message)
        reply = result.get("reply", "")
        correction = result.get("correction")

        log_node(
            trace_id=trace_id,
            node="react_loop",
            input_data={"query": message, "skill": session.mode, "user_level": session.user_level},
            output_data={
                "reply": reply,
                "correction": correction,
                "agentThought": result.get("agentThought"),
            },
            duration_ms=int((_time.perf_counter() - t1) * 1000),
            service=f"Skill[{session.mode}]",
            user_id=int(session.user_id) if str(session.user_id).isdigit() else None,
            session_id=session_id,
        )

        # 记录 Agent 回复
        round_id = f"round_{uuid.uuid4().hex[:8]}"
        react_loop = result.get("react_loop") or []
        natural_summary = _generate_natural_summary(react_loop)
        session.history.append({
            "id": round_id,
            "role": "agent",
            "content": reply,
            "correction": correction,
            "agentThought": result.get("agentThought"),
            "reactLoop": react_loop,
            "naturalSummary": natural_summary,
            "timestamp": _now_iso(),
        })
        session.skill.append_history("agent", reply)

        # P0 根治：每轮落库（多实例下其他实例可恢复）
        if db is not None:
            await self._save_running_async(session, db)

        return {
            "reply": reply,
            "correction": correction,
            "agentThought": result.get("agentThought"),
            "react_loop": react_loop,
            "naturalSummary": natural_summary,
            "decision": decision.decision.value,
            "roundId": round_id,
        }


def _generate_natural_summary(react_loop: list[dict[str, Any]]) -> str:
    """将 ReAct 步骤（Thought → Action → Observation）转为自然语言摘要。

    空循环 → “基于已有知识直接回答。”
    """
    if not react_loop:
        return "基于已有知识直接回答。"

    parts: list[str] = []
    for step in react_loop:
        thought = str(step.get("thought", "")).strip()
        action = str(step.get("action", "")).strip()
        observation = str(step.get("observation", "")).strip()

        if action == "understand_input":
            if thought:
                parts.append(f"我分析了用户的表达：{thought}。")
        elif action == "check_grammar":
            action_desc = "检查了语法" if "grammar" in action else "检查了用词"
            parts.append(f"我调用了语法检查工具，{observation}。")
        elif action == "generate_reply":
            parts.append("我决定先肯定用户的尝试，再温和给出建议与正确表达。")
        else:
            if thought:
                parts.append(f"我思考道：{thought}。")
            if observation:
                parts.append(observation)

    if not parts:
        return "基于已有知识直接回答。"

    # 多步合并：首先…然后…最后…
    if len(parts) == 1:
        return parts[0]
    body = "首先，" + parts[0]
    if len(parts) == 2:
        return body + "然后，" + parts[1]
    for p in parts[1:-1]:
        body += "接着，" + p
    return body + "最后，" + parts[-1]


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
