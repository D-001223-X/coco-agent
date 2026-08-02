"""角色扮演 Skill（T-004）。

Agent 扮演指定角色（服务员、向导等），用户进行场景对话。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import (
    PRACTICE_SYSTEM_PROMPT,
    ROLEPLAY_GREETINGS,
    ROLEPLAY_SCENARIOS,
)
from app.agent.skills.base import BaseSkill

logger = logging.getLogger(__name__)


class RolePlaySkill(BaseSkill):
    """角色扮演 Skill。"""

    SCENARIOS = ROLEPLAY_SCENARIOS
    GREETINGS = ROLEPLAY_GREETINGS

    def get_system_prompt(self, user_message: str = "") -> str:
        scenario_desc = self.SCENARIOS.get(self.scenario, "自由场景")
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '你'}: {h['content']}"
            for h in self.get_history(limit=6)
        ) or "（对话开始）"
        return PRACTICE_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description(),
            mode_label="角色扮演",
            scenario=f"{self.scenario}\n场景描述：{scenario_desc}",
            history=history_text,
            user_message=user_message,
        )

    def get_greeting(self) -> str:
        return self.GREETINGS.get(self.scenario, "你好！很高兴见到你。")

    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """处理用户输入：调用 LLM 生成角色回复 + 纠错。"""
        system_prompt = self.get_system_prompt(user_message)
        raw = await self.call_llm(system_prompt, user_message)
        parsed = self.parse_reply(raw)

        return {
            "reply": parsed["reply"] or "Sorry, could you say that again?",
            "correction": parsed.get("correction"),
            "agentThought": (
                f"角色扮演({self.scenario})，用户等级{self.user_level}，"
                "根据场景设定回应并判断是否需要纠错"
            ),
        }
