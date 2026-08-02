"""陪练会话业务逻辑（T-004）。

管理 Skill 实例、会话状态与 Agent 决策集成。
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
    """会话管理：创建、对话、结束。内存存储（生产可换 Redis/DB）。"""

    def __init__(self) -> None:
        self._sessions: dict[str, PracticeSession] = {}
        self._decision_maker = DecisionMaker()

    # ── 生命周期 ─────────────────────────────────────────
    def start_session(
        self, mode: str, scenario: str, user_level: str, user_id: str
    ) -> tuple[PracticeSession, str]:
        """创建会话，返回 (session, greeting)。"""
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
        return session, greeting

    def get_session(self, session_id: str) -> PracticeSession | None:
        return self._sessions.get(session_id)

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
        if session is not None:
            session.ended_at = time.time()
            if db is not None:
                await self._persist_session_async(session, db)
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

    def switch_scenario(
        self, session_id: str, scenario: str
    ) -> tuple[PracticeSession, str]:
        """切换会话的场景/话题，保留对话历史（T-005）。

        Returns
        -------
        (session, new_greeting)
        """
        session = self.get_session(session_id)
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
        return session, new_greeting

    # ── 对话 ─────────────────────────────────────────────
    async def chat(self, session_id: str, message: str) -> dict[str, Any]:
        """处理用户消息，返回 Agent 回复 + 纠错 + 决策轨迹。"""
        import time as _time

        from app.utils.logger import log_node

        session = self.get_session(session_id)
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
        session.history.append({
            "id": round_id,
            "role": "agent",
            "content": reply,
            "correction": correction,
            "agentThought": result.get("agentThought"),
            "timestamp": _now_iso(),
        })
        session.skill.append_history("agent", reply)

        return {
            "reply": reply,
            "correction": correction,
            "agentThought": result.get("agentThought"),
            "decision": decision.decision.value,
            "roundId": round_id,
        }


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
