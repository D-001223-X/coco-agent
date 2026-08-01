"""Agent 核心能力包（T-001）。

导出决策层、ReAct 循环、工具注册表、记忆与编排器的核心类，
保证 ``from app.agent import *`` 可用。
"""

from app.agent.decision_maker import DecisionMaker
from app.agent.memory import AgentMemory
from app.agent.orchestrator import AgentOrchestrator, AgentSpec
from app.agent.react_loop import ReActLoopExecutor
from app.agent.schemas import (
    AgentDecision,
    AgentDecisionResult,
    ReActLoop,
    ReActStep,
)
from app.agent.tools import (
    TOOLS,
    execute_tool,
    get_tool_schema,
    list_tools,
    register_tool_handler,
)

__all__ = [
    "AgentDecision",
    "AgentDecisionResult",
    "AgentMemory",
    "AgentOrchestrator",
    "AgentSpec",
    "DecisionMaker",
    "ReActLoop",
    "ReActLoopExecutor",
    "ReActStep",
    "TOOLS",
    "execute_tool",
    "get_tool_schema",
    "list_tools",
    "register_tool_handler",
]
