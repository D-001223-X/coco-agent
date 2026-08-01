"""Agent 编排器（Orchestrator，T-001 骨架）。

类 LLMCompiler：多个子 Agent（语法 / 鼓励 / 话题）并行产出，
由 Orchestrator 合并输出。

T-001 阶段仅定义接口与注册机制，子 Agent 在 T-004/T-005 接入。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """子 Agent 注册信息。"""

    name: str
    description: str
    handler: Callable[..., Awaitable[str]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentOrchestrator:
    """多 Agent 并行执行与结果合并。"""

    def __init__(self) -> None:
        self._agents: dict[str, AgentSpec] = {}

    def register(self, spec: AgentSpec) -> None:
        self._agents[spec.name] = spec
        logger.info("[agent] 注册子Agent: %s", spec.name)

    def unregister(self, name: str) -> None:
        self._agents.pop(name, None)

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    async def run_parallel(
        self, inputs: dict[str, dict[str, Any]]
    ) -> dict[str, str]:
        """并行执行多个子 Agent。

        Parameters
        ----------
        inputs : dict[str, dict]
            ``{agent_name: {参数...}}``。

        Returns
        -------
        dict[str, str]
            ``{agent_name: 输出文本}``。
        """
        tasks: dict[str, Awaitable[str]] = {}
        for name, params in inputs.items():
            spec = self._agents.get(name)
            if spec is None or spec.handler is None:
                tasks[name] = _empty_result(f"Agent {name} 未注册")
                continue
            tasks[name] = spec.handler(**params)

        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))

    async def merge(self, outputs: dict[str, str]) -> str:
        """合并各子 Agent 输出为最终回答（TODO: 后续任务实现智能合并）。"""
        if not outputs:
            return ""
        return "\n".join(f"【{k}】{v}" for k, v in outputs.items() if v)


async def _empty_result(msg: str) -> str:
    return msg
