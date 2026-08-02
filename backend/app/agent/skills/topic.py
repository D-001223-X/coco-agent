"""话题讨论 Skill（T-005）。

讨论主题从 ``configs/discussion_topics.py`` 读取（含引入→展开→总结三阶段）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.discussion_topics import DISCUSSION_TOPICS

logger = logging.getLogger(__name__)

# MARKER: TOPIC_PROMPT_START
TOPIC_SYSTEM_PROMPT = """\
你是一位专业的英语口语陪练 Agent，正在与用户进行实时口语对话练习。

## 当前设定
- 用户CEFR等级：{user_level}
- 难度适配：{level_description}
- 陪练模式：话题讨论
- 场景/话题：{scenario}

## 话题讨论规则
1. 围绕主题展开有深度的讨论，避免浅层问答
2. 每轮回复 2-3 句话，先回应观点再追问引导
3. 通过追问（为什么、怎么看、举例）引导用户深入表达观点
4. 适当总结用户观点并给出你的看法

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
# MARKER: TOPIC_PROMPT_END


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

        return TOPIC_SYSTEM_PROMPT.format(
            user_level=self.user_level,
            level_description=self.get_user_level_description()
            + "\n"
            + self.get_difficulty_prompt(),
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

        reply = parsed["reply"] or "That's an interesting point. Why do you think so?"
        correction = parsed.get("correction")
        agent_thought = (
            f"话题讨论[{cfg['name']}]({cfg['category']})，"
            f"用户等级{self.user_level}，难度{cfg['difficulty']}，"
            "按引入→展开→总结结构推进讨论并评价表达"
        )

        return {
            "reply": reply,
            "correction": correction,
            "agentThought": agent_thought,
            "react_loop": self.build_react_loop(
                user_message, reply, correction, agent_thought
            ),
        }
