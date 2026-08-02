"""话题讨论 Skill（T-004）。

给定话题深度讨论，主动追问，拓展表达。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import (
    PRACTICE_SYSTEM_PROMPT,
    TOPIC_DISCUSSIONS,
)
from app.agent.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class TopicSkill(BaseSkill):
    """话题讨论 Skill：深度讨论，拓展表达。"""

    DISCUSSIONS = TOPIC_DISCUSSIONS

    def _guide_questions(self) -> str:
        questions = self.DISCUSSIONS.get(self.scenario, [])
        if not questions:
            return "（自由讨论）"
        return "\n".join(f"- {q}" for q in questions)

    def get_system_prompt(self, user_message: str = "") -> str:
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '你'}: {h['content']}"
            for h in self.get_history(limit=6)
        ) or "（对话开始）"
        return PRACTICE_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description(),
            mode_label="话题讨论",
            scenario=(
                f"话题：{self.scenario}\n"
                f"可引导的问题：\n{self._guide_questions()}"
            ),
            history=history_text,
            user_message=user_message,
        )

    def get_greeting(self) -> str:
        topic = self.scenario or "人工智能的影响"
        return (
            f"Let's discuss {topic}! What do you think about it? "
            f"（我们来聊聊「{topic}」吧，你是怎么看的？）"
        )

    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """深度讨论：回复 + 追问 + 表达评价。"""
        system_prompt = self.get_system_prompt(user_message)
        raw = await self.call_llm(system_prompt, user_message)
        parsed = self.parse_reply(raw)

        return {
            "reply": parsed["reply"] or "That's an interesting point. Why do you think so?",
            "correction": parsed.get("correction"),
            "agentThought": (
                f"话题讨论({self.scenario})，用户等级{self.user_level}，"
                "评估表达深度并给出追问引导"
            ),
        }
