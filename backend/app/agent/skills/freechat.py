"""自由对话 Skill（T-005）。

话题配置从 ``configs/freechat_topics.py`` 读取（含引导问题、难度）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.freechat_topics import FREECHAT_TOPICS

logger = logging.getLogger(__name__)

# MARKER: FREECHAT_PROMPT_START
FREECHAT_SYSTEM_PROMPT = """\
你是一位专业的英语口语陪练 Agent，正在与用户进行实时口语对话练习。

## 当前设定
- 用户CEFR等级：{user_level}
- 难度适配：{level_description}
- 陪练模式：自由对话
- 场景/话题：{scenario}

## 自由对话规则
1. 像朋友一样自然交流，语气轻松友好
2. 每轮回复 1-2 句话，适当追问引导用户展开话题
3. 顺着用户的话题延伸，不要频繁切换主题

## 对话推进规则
1. 每轮回复必须包含至少一个引导性问题
2. 根据用户回复深度调整追问方式
3. 示例：
   - 用户说“I went to the park.” → Agent：“That sounds nice! What did you do at the park？”
   - 用户说“I like reading books.” → Agent：“What kind of books do you like to read？”

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
"""
# MARKER: FREECHAT_PROMPT_END


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

        return FREECHAT_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description()
            + "\n"
            + self.get_difficulty_prompt(),
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
