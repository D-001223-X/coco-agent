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

    def get_difficulty_prompt(self) -> str:
        """根据用户级别返回难度适配的 Prompt 片段（T-005 细化）。"""
        if self.user_level in ["A1", "A2"]:
            return """
## 难度适配规则（A1/A2 用户）
- 使用**基础高频词汇**（如 A1-A2 级词汇）
- 使用**简单句式**（主谓宾结构，1-2 个分句）
- 语速**较慢**，适当重复关键表达
- 每轮回复 1-2 句话
- 纠错时提供清晰示例
- 多使用肯定和鼓励
"""
        return """
## 难度适配规则（B1/B2 用户）
- 使用**中高级词汇**（如 B1-B2 级词汇）
- 使用**复合句式**（含从句，3-4 个分句）
- **正常语速**，自然节奏
- 每轮回复 2-3 句话
- 纠错仅针对高频/严重错误
- 鼓励更完整表达和观点阐述
"""

    def switch_context(self, scenario: str) -> None:
        """切换场景/话题，保留对话历史（T-005 动态切换）。"""
        self.scenario = scenario
        # 历史保留；可清空场景内的中间状态（如有）

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
        """解析 LLM 输出：第一行为回复，后续可选 CORRECTION / THINK 行。

        Returns
        -------
        dict
            ``{"reply": str, "correction": dict|None, "steps": list|None}``
            steps: 真实 ReAct 思考链（多步 thought/tool/observation），
            由 LLM 当次生成；缺失时回退模板（build_react_loop 兜底）。
        """
        lines = [ln.strip() for ln in (raw or "").split("\n") if ln.strip()]
        reply = lines[0] if lines else ""
        correction = None
        steps: list[dict[str, Any]] | None = None
        for ln in lines[1:]:
            if ln.startswith("CORRECTION:"):
                try:
                    correction = json.loads(ln[len("CORRECTION:"):].strip())
                except json.JSONDecodeError:
                    correction = None
            elif ln.startswith("THINK:"):
                try:
                    raw_steps = json.loads(ln[len("THINK:"):].strip())
                    if isinstance(raw_steps, list) and raw_steps:
                        steps = [
                            {
                                "thought": str(s.get("thought", "")),
                                "tool": str(s.get("tool", "")),
                                "observation": str(s.get("observation", "")),
                            }
                            for s in raw_steps[:4]
                            if isinstance(s, dict)
                        ]
                        if not steps:
                            steps = None
                except json.JSONDecodeError:
                    steps = None
        return {"reply": reply, "correction": correction, "steps": steps}

    @staticmethod
    def summarize_thoughts(
        react_loop: list[dict[str, Any]],
        fallback: str = "",
    ) -> str:
        """从 ReAct 步骤生成文本摘要（Agent 思考折叠内容）。

        真实步骤：拼接 thought / tool(action) / observation；
        空链回退 *fallback*。
        """
        if not react_loop:
            return fallback
        parts: list[str] = []
        for i, s in enumerate(react_loop, 1):
            seg: list[str] = []
            thought = str(s.get("thought", "")).strip()
            tool = str(s.get("action", "")).strip()
            obs = str(s.get("observation", "")).strip()
            if thought:
                seg.append(thought)
            if tool:
                seg.append(f"工具：{tool}")
            if obs:
                seg.append(f"观察：{obs}")
            if seg:
                parts.append(f"{i}. {'；'.join(seg)}")
        return "\n".join(parts) if parts else fallback

    @staticmethod
    def validate_correction(
        correction: dict[str, Any] | None,
        user_message: str,
    ) -> dict[str, Any] | None:
        """纠错防线：仅保留针对「当前最新消息」的纠错。

        若 LLM 对历史旧内容纠错（original 不在当前消息中），丢弃之，
        避免出现“针对旧的内容纠错”的错位体验（P1 修复）。

        注意：使用大小写不敏感匹配——LLM 常把 original 规范化为小写，
        而用户输入可能含大写，避免误杀合法纠错（P5 修复）。
        """
        if not correction:
            return None
        orig = str(correction.get("original", "")).strip()
        if not orig:
            return None
        if orig.lower() not in user_message.lower():
            return None
        return correction

    def build_react_loop(
        self,
        user_message: str,
        reply: str,
        correction: dict | None,
        agent_thought: str,
        trace_steps: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """构造 ReAct 循环步骤（Thought → Action → Observation）。

        优先使用 LLM 当次生成的 ``trace_steps``（真实思考链：
        thought=思考内容 / tool=用的工具 / observation=观察结果）；
        缺失时回退到模板步骤（兼容旧输出）。

        Returns
        -------
        list[dict]
            步骤列表（step/thought/action/action_input/observation）
        """
        # 真实思考链（LLM 当次输出）：thought/tool/observation 原样保留
        if trace_steps:
            return [
                {
                    "step": i + 1,
                    "thought": s.get("thought", ""),
                    "action": s.get("tool", ""),
                    "action_input": {"text": user_message},
                    "observation": s.get("observation", ""),
                }
                for i, s in enumerate(trace_steps)
            ]

        # ── 模板兜底（LLM 未输出 THINK 时）──────────────────
        steps: list[dict[str, Any]] = []

        # Step 1: 理解用户输入
        steps.append({
            "step": 1,
            "thought": f"分析用户输入，识别其表达意图和可能的语言问题",
            "action": "understand_input",
            "action_input": {"text": user_message},
            "observation": f"用户等级 {self.user_level}，场景「{self.scenario}」",
        })

        if correction:
            # Step 2: 语法/词汇检查
            steps.append({
                "step": 2,
                "thought": agent_thought or "用户表达存在可优化之处，需要检查语言准确性",
                "action": "check_grammar",
                "action_input": {"text": correction.get("original", user_message)},
                "observation": (
                    f"发现{correction.get('type', '语法')}问题："
                    f"「{correction.get('original', '')}」应改为「{correction.get('corrected', '')}」"
                ),
            })
            # Step 3: 生成含纠错的回复
            steps.append({
                "step": 3,
                "thought": "决定先肯定用户的尝试，再温和指出错误并给出正确表达",
                "action": "generate_reply",
                "action_input": {"with_correction": True},
                "observation": f"已生成回复：{reply[:60]}{'...' if len(reply) > 60 else ''}",
            })
        else:
            # Step 2: 直接生成回复
            steps.append({
                "step": 2,
                "thought": agent_thought or "用户表达正确，基于场景直接生成自然回复并继续引导对话",
                "action": "generate_reply",
                "action_input": {"with_correction": False},
                "observation": f"已生成回复：{reply[:60]}{'...' if len(reply) > 60 else ''}",
            })

        return steps
