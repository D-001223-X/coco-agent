"""Agent 决策层（Decision Maker，T-001）。

根据意图识别结果（intent + confidence）与查询特征，决定执行路径：
  - 高置信度 + 简单问题 → SIMPLE_ANSWER（直接回答）
  - 低置信度          → CLARIFY（追问澄清）
  - 默认              → DEEP_REASONING（深度推理，回退到现有工作流）

T-001 阶段为规则实现；后续可接入 LLM 决策（decision_prompt）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.prompts.decision_prompt import DECISION_PROMPT
from app.agent.schemas import AgentDecision, AgentDecisionResult

logger = logging.getLogger(__name__)

# 简单问题特征词（命中即视为可直接回答）
_SIMPLE_PATTERNS = ("多少钱", "是什么", "怎么", "哪里", "谁", "多少", "吗")


class DecisionMaker:
    """根据意图与置信度选择 Agent 行动路径。"""

    async def decide(
        self,
        query: str,
        intent: str,
        confidence: float,
        context: str = "",
    ) -> AgentDecisionResult:
        """决策入口。

        Parameters
        ----------
        query : str
            用户问题（建议传入已消解指代的 resolved_question）。
        intent : str
            意图识别结果（SUPPORT / FEEDBACK / CHAT 等）。
        confidence : float
            意图置信度（0.0-1.0）。
        context : str
            额外上下文（对话历史等），供后续 LLM 决策使用。
        """
        # 1. 高置信度简单问题 → 直接回答
        if confidence > 0.85 and self._is_simple_query(query):
            return AgentDecisionResult(
                decision=AgentDecision.SIMPLE_ANSWER,
                reason="高置信度，简单问题",
                confidence=confidence,
                fallback_to_workflow=False,
            )

        # 2. 低置信度 → 追问澄清
        if confidence < 0.5:
            return AgentDecisionResult(
                decision=AgentDecision.CLARIFY,
                reason="置信度低，需要追问",
                confidence=confidence,
                fallback_to_workflow=False,
            )

        # 3. 默认：深度推理（回退到现有 RAG 工作流）
        return AgentDecisionResult(
            decision=AgentDecision.DEEP_REASONING,
            reason="Agent自主决定走深度推理路径",
            confidence=confidence,
            fallback_to_workflow=True,
        )

    def _is_simple_query(self, query: str) -> bool:
        """判断查询是否为简单问题（含特征词即命中）。"""
        return any(p in query for p in _SIMPLE_PATTERNS)

    async def decide_with_llm(
        self, query: str, context: str = ""
    ) -> AgentDecisionResult:
        """LLM 决策（预留）：调用 DeepSeek 解析决策结果。

        T-001 不调用 API；该方法保留接口，后续任务接入真实实现。
        """
        prompt = DECISION_PROMPT.format(query=query, context=context or "（无）")
        logger.info("[agent] LLM 决策预留，prompt=%s", prompt[:120])
        raise NotImplementedError("LLM 决策将在后续任务中实现（T-001 不调用 API）")
