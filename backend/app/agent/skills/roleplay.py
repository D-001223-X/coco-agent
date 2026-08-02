"""角色扮演 Skill（T-005）。

场景配置从 ``configs/roleplay_scenarios.py`` 读取（含角色性格、难度、开场白）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.practice_prompts import ROLEPLAY_GREETINGS
from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.roleplay_scenarios import ROLEPLAY_SCENARIOS

logger = logging.getLogger(__name__)

# MARKER: ROLEPLAY_PROMPT_START
ROLEPLAY_SYSTEM_PROMPT = """\
你是一位专业的英语口语陪练 Agent，正在与用户进行实时口语对话练习。

## 当前设定
- 用户CEFR等级：{user_level}
- 难度适配：{level_description}
- 陪练模式：角色扮演
- 场景/话题：{scenario}

## 角色扮演规则
1. 完全进入角色，符合场景身份（如服务员、向导、前台、店员、面试官）
2. 保持角色性格设定，每轮回复 1-2 句话
3. 通过追问引导用户完成场景任务（点餐、问路、入住、购物、面试）

## 纠错策略（重要）
1. 用户出现语法/用词/表达错误时，温和指出并给出正确表达，格式："Good try! Actually, we say '...'"
2. 如果用户表达正确，给予简短肯定（如 "Great!" / "Nice!"），可顺带提供一个更地道的说法
3. 先肯定再纠正，不要打击用户信心

## 输出格式
第一行：你的对话回复（1-2句）
第二行（如有纠错）：CORRECTION: {{"original": "原句", "corrected": "正确表达", "type": "grammar|vocabulary|pronunciation"}}
如果没有纠错，只输出第一行。

## 对话历史
{history}

## 用户最新消息
{user_message}
（测试追加行）
"""
# MARKER: ROLEPLAY_PROMPT_END


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

        return ROLEPLAY_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description()
            + "\n"
            + self.get_difficulty_prompt(),
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

        reply = parsed["reply"] or "Sorry, could you say that again?"
        correction = parsed.get("correction")
        agent_thought = (
            f"角色扮演[{cfg['name']}]({cfg['role']})，"
            f"用户等级{self.user_level}，难度{cfg['difficulty']}，"
            "根据角色性格回应并判断是否需要纠错"
        )

        return {
            "reply": reply,
            "correction": correction,
            "agentThought": agent_thought,
            "react_loop": self.build_react_loop(
                user_message, reply, correction, agent_thought
            ),
        }
