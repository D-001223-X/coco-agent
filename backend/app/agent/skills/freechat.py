"""自由对话 Skill（T-005）。

话题配置从 ``configs/freechat_topics.py`` 读取（含引导问题、难度）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import PRACTICE_SYSTEM_PROMPT
from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.freechat_topics import FREECHAT_TOPICS

logger = logging.getLogger(__name__)


class FreeChatSkill(BaseSkill):
    """自由对话 Skill：话题配置驱动 + 引导问题。"""

    TOPICS = FREECHAT_TOPICS

    def _topic_cfg(self) -> dict:
        for cfg in self.TOPICS.values():
            if self.scenario in (cfg["id"], cfg["name"]):
                return cfg
        return next(iter(self.TOPICS.values()))

    def get_system_prompt(self, user_message: str = "") -> str:
        cfg = self._topic_cfg()
        guiding = "\n".join(f"- {q}" for q in cfg.get("guiding_questions", []))
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '你'}: {h['content']}"
            for h in self.get_history(limit=6)
        ) or "（对话开始）"

        return PRACTICE_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description()
            + "\n"
            + self.get_difficulty_prompt(),
            mode_label="自由对话",
            scenario=(
                f"话题：{cfg['name']}\n"
                f"话题描述：{cfg['description']}\n"
                f"可引导的问题：\n{guiding}"
            ),
            history=history_text,
            user_message=user_message,
        )

    def get_greeting(self) -> str:
        cfg = self._topic_cfg()
        return (
            f"Hi! Let's chat about {cfg['name']}! "
            f"（我们今天聊聊「{cfg['name']}」吧，随意说说你的想法~）"
        )

    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """自然对话 + 精准纠错 + 话题引导。"""
        cfg = self._topic_cfg()
        system_prompt = self.get_system_prompt(user_message)
        raw = await self.call_llm(system_prompt, user_message)
        parsed = self.parse_reply(raw)

        reply = parsed["reply"] or "Interesting! Tell me more."
        correction = parsed.get("correction")
        agent_thought = (
            f"自由对话[{cfg['name']}]({cfg['category']})，"
            f"用户等级{self.user_level}，难度{cfg['difficulty']}，"
            "自然引导话题并轻量纠错"
        )

        return {
            "reply": reply,
            "correction": correction,
            "agentThought": agent_thought,
            "react_loop": self.build_react_loop(
                user_message, reply, correction, agent_thought
            ),
        }
