"""Agent ReAct 循环（T-001）。

实现 Thought → Action → Observation 循环：
  - 每步调用 LLM 生成 Thought/Action（T-001 用模拟逻辑占位）
  - 执行工具获取 Observation
  - 早停机制（_should_finish）
  - 最大迭代上限（默认 5，遵守红线约束）

T-001 阶段不调用 DeepSeek API，循环使用模拟 Thought 与工具模拟结果。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.react_prompt import REACT_PROMPT
from app.agent.schemas import ReActLoop, ReActStep
from app.agent.tools import execute_tool, list_tools

logger = logging.getLogger(__name__)

_MAX_STEPS = 5  # 红线：ReAct 循环不超过 5 次迭代


class ReActLoopExecutor:
    """改进版 ReAct：Thought → Action → Observation，带早停。"""

    def __init__(self, max_steps: int = _MAX_STEPS) -> None:
        self.max_steps = max_steps

    async def run(self, query: str, context: str = "") -> ReActLoop:
        """执行 ReAct 循环。

        Parameters
        ----------
        query : str
            用户问题。
        context : str
            对话历史等上下文。

        Returns
        -------
        ReActLoop
            包含全部步骤与最终答案的循环记录。
        """
        steps: list[ReActStep] = []
        final_answer: str | None = None

        for step_num in range(1, self.max_steps + 1):
            # TODO(T-004): 调用 LLM 生成 Thought 和 Action
            thought = f"思考：分析用户问题 '{query}'"
            action = "search_knowledge"
            action_input: dict[str, Any] = {"query": query}

            observation = await execute_tool(action, action_input)

            step = ReActStep(
                step=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
            )
            steps.append(step)
            logger.info(
                "[agent] ReAct step=%d action=%s obs=%s",
                step_num, action, observation[:60],
            )

            # 早停判断
            if self._should_finish(observation):
                final_answer = observation
                break

        return ReActLoop(
            steps=steps,
            max_steps=self.max_steps,
            final_answer=final_answer,
        )

    def _should_finish(self, observation: str) -> bool:
        """早停逻辑：观测结果非空即认为可作答（TODO: 增强判断）。"""
        return len(observation) > 0

    def build_react_prompt(self, query: str, context: str = "") -> str:
        """构造 ReAct Prompt（供 LLM 调用方使用）。"""
        tools_desc = "\n".join(
            f"- {t['name']}: {t['description']}" for t in list_tools()
        )
        return REACT_PROMPT.format(
            tools=tools_desc, query=query, context=context or "（无）"
        )
