"""话题讨论 Skill（T-005）。

讨论主题从 ``configs/discussion_topics.py`` 读取（含引入→展开→总结三阶段）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import PRACTICE_SYSTEM_PROMPT
from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.discussion_topics import DISCUSSION_TOPICS

logger = logging.getLogger(__name__)


class TopicSkill(BaseSkill):
    """话题讨论 Skill：结构化讨论（引入→展开→总结）。"""

    DISCUSSIONS = DISCUSSION_TOPICS

    def _topic_cfg(self) -> dict:
        for cfg in self.DISCUSSIONS.values():
            if self.scenario in (cfg["id"], cfg["name"]):
                return cfg
        return next(iter(self.DISCUSSIONS.values()))

    def _structure_text(self) -> str:
        cfg = self._topic_cfg()
        expansion = "\n".join(f"- {q}" for q in cfg.get("expansion_questions", []))
        return (
            f"引入：{cfg.get('introduction', '')}\n"
            f"展开问题：\n{expansion}\n"
            f"总结引导：{cfg.get('summary_prompt', '总结你的观点')}"
        )

    def get_system_prompt(self, user_message: str = "") -> str:
        cfg = self._topic_cfg()
        history_text = "\n".join(
            f"{'用户' if h['role'] == 'user' else '你'}: {h['content']}"
            for h in self.get_history(limit=6)
        ) or "（对话开始）"

        return PRACTICE_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description()
            + "\n"
            + self.get_difficulty_prompt(),
            mode_label="话题讨论",
            scenario=f"话题：{cfg['name']}\n讨论结构：\n{self._structure_text()}",
            history=history_text,
            user_message=user_message,
        )

    def get_greeting(self) -> str:
        cfg = self._topic_cfg()
        return (
            f"Let's discuss {cfg['name']}! {cfg.get('introduction', '')} "
            f"（我们来聊聊「{cfg['name']}」吧，你是怎么看的？）"
        )

    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """深度讨论：回复 + 追问 + 表达评价。"""
        cfg = self._topic_cfg()
        system_prompt = self.get_system_prompt(user_message)
        raw = await self.call_llm(system_prompt, user_message)
        parsed = self.parse_reply(raw)

        return {
            "reply": parsed["reply"] or "That's an interesting point. Why do you think so?",
            "correction": parsed.get("correction"),
            "agentThought": (
                f"话题讨论[{cfg['name']}]({cfg['category']})，"
                f"用户等级{self.user_level}，难度{cfg['difficulty']}，"
                "按引入→展开→总结结构推进讨论并评价表达"
            ),
        }
