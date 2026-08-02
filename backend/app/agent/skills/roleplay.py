"""角色扮演 Skill（T-005）。

场景配置从 ``configs/roleplay_scenarios.py`` 读取（含角色性格、难度、开场白）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import (
    PRACTICE_SYSTEM_PROMPT,
    ROLEPLAY_GREETINGS,
)
from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.roleplay_scenarios import ROLEPLAY_SCENARIOS

logger = logging.getLogger(__name__)


class RolePlaySkill(BaseSkill):
    """角色扮演 Skill：场景配置驱动。"""

    SCENARIOS = ROLEPLAY_SCENARIOS

    def _scenario_cfg(self) -> dict:
        """当前场景配置（按 id 或名称匹配）。"""
        for cfg in self.SCENARIOS.values():
            if self.scenario in (cfg["id"], cfg["name"]):
                return cfg
        # 兜底：第一个场景
        return next(iter(self.SCENARIOS.values()))

    def get_system_prompt(self, user_message: str = "") -> str:
        cfg = self._scenario_cfg()
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '你'}: {h['content']}"
            for h in self.get_history(limit=6)
        ) or "（对话开始）"

        return PRACTICE_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description()
            + "\n"
            + self.get_difficulty_prompt(),
            mode_label="角色扮演",
            scenario=(
                f"场景：{cfg['name']}\n"
                f"你的角色：{cfg['role']}\n"
                f"角色性格：{cfg['system_prompt_additions']}\n"
                f"场景描述：{cfg['description']}"
            ),
            history=history_text,
            user_message=user_message,
        )

    def get_greeting(self) -> str:
        cfg = self._scenario_cfg()
        return cfg.get("opening") or ROLEPLAY_GREETINGS.get(self.scenario, "你好！很高兴见到你。")

    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """处理用户输入：调用 LLM 生成角色回复 + 纠错。"""
        cfg = self._scenario_cfg()
        system_prompt = self.get_system_prompt(user_message)
        raw = await self.call_llm(system_prompt, user_message)
        parsed = self.parse_reply(raw)

        return {
            "reply": parsed["reply"] or "Sorry, could you say that again?",
            "correction": parsed.get("correction"),
            "agentThought": (
                f"角色扮演[{cfg['name']}]({cfg['role']})，"
                f"用户等级{self.user_level}，难度{cfg['difficulty']}，"
                "根据角色性格回应并判断是否需要纠错"
            ),
        }
