"""自由对话 Skill（T-004）。

用户自选话题，自然对话，随时纠错。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import (
    FREECHAT_TOPICS,
    PRACTICE_SYSTEM_PROMPT,
)
from app.agent.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class FreeChatSkill(BaseSkill):
    """自由对话 Skill：自选话题，自然交流。"""

    TOPICS = FREECHAT_TOPICS

    def get_system_prompt(self, user_message: str = "") -> str:
        topic = self.scenario or "自由话题"
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '你'}: {h['content']}"
            for h in self.get_history(limit=6)
        ) or "（对话开始）"
        return PRACTICE_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description(),
            mode_label="自由对话",
            scenario=f"话题：{topic}",
            history=history_text,
            user_message=user_message,
        )

    def get_greeting(self) -> str:
        topic = self.scenario or "你的一天"
        return f"Hi! Let's chat about {topic}. What would you like to say? (我们今天聊聊「{topic}」吧，随意说说你的想法~)"

    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """自然对话 + 纠错。"""
        system_prompt = self.get_system_prompt(user_message)
        raw = await self.call_llm(system_prompt, user_message)
        parsed = self.parse_reply(raw)

        return {
            "reply": parsed["reply"] or "Interesting! Tell me more.",
            "correction": parsed.get("correction"),
            "agentThought": (
                f"自由对话(话题:{self.scenario or '自由'})，"
                f"用户等级{self.user_level}，自然引导话题并轻量纠错"
            ),
        }
