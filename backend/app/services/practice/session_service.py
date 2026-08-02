"""陪练会话业务逻辑（T-004）。

管理 Skill 实例、会话状态与 Agent 决策集成。
"""

from __future__ import annotations

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
        return session

    # ── 对话 ─────────────────────────────────────────────
    async def chat(self, session_id: str, message: str) -> dict[str, Any]:
        """处理用户消息，返回 Agent 回复 + 纠错 + 决策轨迹。"""
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"会话不存在: {session_id}")

        # Agent 决策层集成：判断走直接回复（SIMPLE_ANSWER）还是深度处理
        decision = await self._decision_maker.decide(
            query=message,
            intent="PRACTICE",
            confidence=0.9,  # 陪练场景置信度固定偏高（消息都是练习输入）
            context="口语陪练",
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

        # Skill 处理
        result = await session.skill.process_user_input(message)
        reply = result.get("reply", "")
        correction = result.get("correction")

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
