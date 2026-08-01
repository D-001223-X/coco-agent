"""Agent 数据契约（T-001）。

定义 Agent 决策层 / ReAct 循环 / 工具注册表使用的 Pydantic 模型。
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class AgentDecision(str, Enum):
    """Agent 决策路径。"""

    SIMPLE_ANSWER = "simple_answer"
    DEEP_REASONING = "deep_reasoning"
    CLARIFY = "clarify"
    COMPLEX_PLAN = "complex_plan"


class ReActStep(BaseModel):
    """ReAct 循环中的单步：Thought → Action → Observation。"""

    step: int
    thought: str
    action: str
    action_input: Any
    observation: str


class ReActLoop(BaseModel):
    """完整的 ReAct 循环记录。"""

    steps: list[ReActStep]
    max_steps: int = 5
    final_answer: Optional[str] = None


class AgentDecisionResult(BaseModel):
    """决策层输出。"""

    decision: AgentDecision
    reason: str
    confidence: float
    fallback_to_workflow: bool = False
