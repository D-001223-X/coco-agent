"""Skill 基类（T-004）。

所有陪练 Skill 的抽象基类。每个 Skill 提供：
  - get_system_prompt()  系统 Prompt（含难度适配规则）
  - get_greeting()       场景开场白
  - process_user_input() 处理用户输入，返回 Agent 回复 + 纠错

注意：Skill 实例由 session_service 持有，负责调用 DeepSeek 生成回复。
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_LEVEL_DESCRIPTIONS = {
    "A1": "使用最基础的词汇和简单句，放慢节奏，适当重复，多给鼓励",
    "A2": "使用基础词汇和简单句式，多引导和重复，鼓励完整表达",
    "B1": "使用常用中高级词汇，复合句式，自然语速，适度纠错",
    "B2": "使用丰富的词汇和复杂句式，自然语速，重点纠高频错误",
}


class BaseSkill(ABC):
    """所有 Skill 的基类。"""

    def __init__(self, user_level: str, scenario: str = "") -> None:
        self.user_level = user_level.upper() if user_level else "A2"
        if self.user_level not in _LEVEL_DESCRIPTIONS:
            self.user_level = "A2"
        self.scenario = scenario
        self.conversation_history: list[dict[str, str]] = []
        self._settings = get_settings()

    # ── 抽象接口 ─────────────────────────────────────────
    @abstractmethod
    def get_system_prompt(self) -> str:
        """返回 Skill 的 System Prompt。"""
        raise NotImplementedError

    @abstractmethod
    def get_greeting(self) -> str:
        """返回场景开场白。"""
        raise NotImplementedError

    @abstractmethod
    async def process_user_input(self, user_message: str) -> dict[str, Any]:
        """处理用户输入，返回 Agent 回复 + 纠错信息。

        Returns
        -------
        dict
            ``{"reply": str, "correction": dict|None, "agentThought": str}``
        """
        raise NotImplementedError

    # ── 公共方法 ─────────────────────────────────────────
    def get_user_level_description(self) -> str:
        """根据用户级别返回难度描述。"""
        return _LEVEL_DESCRIPTIONS.get(
            self.user_level,
            "使用基础词汇和简单句式，多引导和重复",
        )

    def append_history(self, role: str, content: str) -> None:
        """追加对话历史（user / agent）。"""
        self.conversation_history.append({"role": role, "content": content})

    def get_history(self, limit: int | None = None) -> list[dict[str, str]]:
        """获取对话历史（最近 *limit* 条）。"""
        if limit is None:
            return list(self.conversation_history)
        return list(self.conversation_history[-limit:])

    # ── LLM 调用辅助 ─────────────────────────────────────
    async def call_llm(self, system_prompt: str, user_message: str) -> str:
        """调用 DeepSeek 生成回复；无 API key 时返回模拟回复。"""
        s = self._settings
        if not s.dashscope_api_key:
            logger.info("[skill] 无 API key，返回模拟回复")
            return (
                f"（模拟回复）你说了：{user_message[:50]}。很好！"
                f"继续对话吧。"
            )

        payload: dict[str, Any] = {
            "model": s.deepseek_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 512,
        }
        headers = {
            "Authorization": f"Bearer {s.dashscope_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{s.deepseek_base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return "I'm sorry, I couldn't respond. Please try again."
            return choices[0]["message"]["content"].strip()
        except Exception as exc:
            logger.warning("[skill] LLM 调用失败: %s", exc)
            return "Sorry, I didn't catch that. Could you say it again?"

    @staticmethod
    def parse_reply(raw: str) -> dict[str, Any]:
        """解析 LLM 输出：第一行为回复，第二行（可选）为纠错 JSON。

        Returns
        -------
        dict
            ``{"reply": str, "correction": dict|None}``
        """
        lines = [ln.strip() for ln in (raw or "").split("\n") if ln.strip()]
        reply = lines[0] if lines else ""
        correction = None
        for ln in lines[1:]:
            if ln.startswith("CORRECTION:"):
                try:
                    correction = json.loads(ln[len("CORRECTION:"):].strip())
                except json.JSONDecodeError:
                    correction = None
                break
        return {"reply": reply, "correction": correction}
