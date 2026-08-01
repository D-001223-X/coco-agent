"""Agent 工具注册表（T-001）。

T-001 阶段仅注册工具定义，``execute_tool`` 返回模拟数据，
禁止在 T-001 中调用 DeepSeek API（后续任务接入真实实现）。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

TOOLS: dict[str, dict[str, Any]] = {
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "在知识库中搜索信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "top_k": {"type": "integer", "description": "返回结果数量，默认3"},
            },
            "required": ["query"],
        },
    },
    "check_grammar": {
        "name": "check_grammar",
        "description": "检查英语语法错误",
        "parameters": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "要检查的英文文本"},
            },
            "required": ["text"],
        },
    },
    "lookup_word": {
        "name": "lookup_word",
        "description": "查询英文单词的含义和用法",
        "parameters": {
            "type": "object",
            "properties": {
                "word": {"type": "string", "description": "要查询的英文单词"},
            },
            "required": ["word"],
        },
    },
}

# 工具名 → 可执行函数（后续任务逐步注册真实实现）
_TOOL_HANDLERS: dict[str, Any] = {}


def register_tool_handler(tool_name: str, handler: Any) -> None:
    """注册工具的真实执行函数（供后续任务调用）。"""
    _TOOL_HANDLERS[tool_name] = handler


def list_tools() -> list[dict[str, Any]]:
    """返回全部已注册工具定义。"""
    return list(TOOLS.values())


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """按名称获取工具定义。"""
    return TOOLS.get(tool_name)


async def execute_tool(tool_name: str, params: dict[str, Any]) -> str:
    """执行工具，返回字符串结果。

    T-001：若工具已有真实 handler 则调用；否则返回模拟数据。
    """
    handler = _TOOL_HANDLERS.get(tool_name)
    if handler is not None:
        result = handler(**params)
        if hasattr(result, "__await__"):
            return str(await result)
        return str(result)

    logger.info("[agent] 工具 %s 尚无真实实现，返回模拟数据: %s", tool_name, params)
    return f"工具 {tool_name} 执行结果（模拟）"
