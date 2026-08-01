"""Intent recognition service — classifies user queries into SUPPORT / FEEDBACK / CHAT.

Architecture:
  • Calls DeepSeek (via Alibaba DashScope compatible-mode gateway) with a
    carefully crafted system prompt.
  • Resolves coreferences from conversation history so follow-up questions
    like "它多少钱？" are expanded into self-contained queries.
  • Degrades gracefully: on any error (timeout, HTTP error, JSON parse
    failure) the intent falls back to CHAT with confidence 0.0.
  • Every call is logged via ``log_node`` (fire-and-forget, non-blocking).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from app.config import get_settings
from app.services.admin.prompt_service import load_prompt
from app.utils.logger import log_node

logger = logging.getLogger(__name__)

# ── Enums / constants ─────────────────────────────────────
INTENT_SUPPORT = "SUPPORT"
INTENT_FEEDBACK = "FEEDBACK"
INTENT_CHAT = "CHAT"
_VALID_INTENTS = {INTENT_SUPPORT, INTENT_FEEDBACK, INTENT_CHAT}


# ── Response dataclass ───────────────────────────────────
@dataclass
class IntentResult:
    """Structured result returned by ``IntentService.recognize``."""

    intent: str
    confidence: float
    resolved_question: str
    reason: str
    related_sections: list[str] | None = None
    reference_candidates: list[dict] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ── System prompt (需求规格书 §8.1) ──────────────────────
# MARKER: INTENT_PROMPT_START
SYSTEM_PROMPT = """\
你是"可可语伴"AI智能客服系统的意图识别引擎。你的任务是分析用户的最新消息，结合对话历史，准确判断用户意图并输出结构化 JSON。

## 一、角色定义

你是客服系统的第一道关卡。你的判断结果将决定后续路由：
- SUPPORT → 进入知识库检索流程（RAG）
- FEEDBACK → 进入反馈收集流程
- CHAT → 直接由大模型生成闲聊回复（不检索知识库）

## 二、指代消解规则

用户在多轮对话中经常使用代词或省略主语。你必须结合对话历史，将指代消解后的问题写入 resolved_question 字段。

规则：
1. 如果用户说"它""这个""那个""上面提到的"等代词，必须根据历史上下文还原为具体指代对象，且优先指向最近一次明确提及的对象。
2. 如果用户消息本身已经完整自足，不需要消解，则 resolved_question 直接使用原始 query。
3. 消解后的 resolved_question 必须是一个完整、独立、不依赖上下文就能理解的问题或陈述。

示例：
- 历史: "会员多少钱？" → 当前: "学生有优惠吗？" → resolved_question: "可可语伴会员学生有优惠吗？"
- 历史: "怎么收藏句子？" → 当前: "那怎么复习？" → resolved_question: "怎么复习收藏的句子？"
- 无历史 → 当前: "会员多少钱？" → resolved_question: "会员多少钱？"

## 三、意图分类标准

### SUPPORT（产品支持类）
用户在询问或寻求帮助解决与"可可语伴"产品相关的具体信息类问题。包括但不限于：
- 产品功能咨询（怎么用、有什么功能、支持什么语言）
- 价格与套餐咨询（会员多少钱、免费版有什么、家庭套餐）
- 使用教程与操作指引（怎么收藏、怎么复习、怎么切换语言）
- 产品对比与差异化（和百词斩区别、和ChatGPT区别）
- 账号与登录问题（忘记密码、切换设备、数据同步）

关键特征：用户期望获得关于产品的**信息或操作指导**，而非报告问题。

### FEEDBACK（反馈建议类）
用户在报告问题、表达不满或提出改进建议。包括但不限于：
- 故障与技术问题（没有声音、打不开、闪退、无法登录）
- 功能建议（希望增加XX功能、建议改进XX）
- 体验反馈（不好用、太卡了、希望优化）
- Bug报告（遇到XX报错、XX不工作）
- 投诉与不满（对服务不满意、退款请求）
- 账号与会员问题（会员过期了、忘了密码）

关键特征：用户在**陈述问题或表达诉求**，而非单纯询问产品信息。

### CHAT（闲聊类）
用户在进行与产品无关的日常交流，或表达情绪、状态。包括但不限于：
- 问候（你好、早上好、嗨）
- 情绪表达（今天心情不好、好累、开心）
- 闲聊（天气怎么样、你是谁、讲个笑话、你会做饭吗）
- 跑题内容（与可可语伴产品完全无关的对话，如编程问题、历史、地理等）
- **知识库未覆盖的问题**（如问创始人是谁、公司成立时间等产品介绍中未提及的信息）

关键特征：不涉及产品功能咨询，也不涉及反馈建议，纯粹是社交性对话或**不属于产品知识范围的提问**。

## 四、输出格式

你必须且只能输出一个合法的 JSON 对象，不要输出任何其他内容（不要 markdown 代码块标记，不要解释文字）。JSON 结构如下：

{
  "intent": "SUPPORT | FEEDBACK | CHAT",
  "confidence": 0.0到1.0之间的浮点数,
  "resolved_question": "消解指代后的完整问题",
  "reason": "简要说明为什么判断为该意图",
  "related_sections": ["知识库中与问题相关的章节标题数组，无匹配时为空数组"],
  "reference_candidates": [
    {
      "target": "指代对象名称",
      "attributes": {"key": "value"},
      "confidence": 0.0到1.0之间的浮点数
    }
  ]
}

related_sections 说明：
- 从知识库章节标题中识别与用户问题最相关的 1-3 个章节（如"五、会员与付费方案"、"六、使用指南"）。
- 如果无法确定对应章节，输出空数组 []。
- 该字段用于限定检索范围，提高检索精度。

reference_candidates 说明：
- 用户使用代词（"他/她/它/这个/那个"）或模糊表达（"太贵了/有点贵/怎么用"）时，输出可能的指代对象及其置信度。
- 无指代或无法确定时输出空数组 []。
- 详见"五、多目标指代候选规则"。

confidence 评分标准：
- 0.9-1.0：意图非常明确，无歧义
- 0.7-0.89：意图较明确，但有轻微不确定
- 0.5-0.69：意图模糊，但有倾向性
- 低于0.5：高度不确定

注意：CHAT 类型的 confidence 不要高于 0.6，以防止将误判的闲聊导向跳过知识库检索。
当用户问题涉及产品信息（如创始团队、公司背景、技术细节、服务器等），即使知识库中暂无相关信息，也应归类为 SUPPORT 而非 CHAT。

## 五、多目标指代候选规则

当用户使用代词（如"他"、"这个"、"那个"）或模糊表达（如"有点贵"、"太贵了"）时：

1. 如果对话历史中只存在一个明确的指代对象 → reference_candidates 只输出该对象，confidence ≥ 0.9
2. 如果对话历史中存在多个可能的指代对象 → 在 reference_candidates 中列出所有可能对象及其置信度（按相关性排序）
3. 如果无法确定任何指代对象 → reference_candidates 输出空数组 []

示例 1（多个候选）：
对话历史：
- 用户："会员多少钱" → 系统："基础会员68元/月，大会员168元/月"
- 用户："他这么贵啊"
输出 reference_candidates：
[
  {"target": "基础会员", "attributes": {"price": "68元/月"}, "confidence": 0.30},
  {"target": "大会员", "attributes": {"price": "168元/月"}, "confidence": 0.60}
]

示例 2（单个候选）：
对话历史：
- 用户："基础会员包含哪些权益" → 系统："包含无限对话时长、全部角色扮演场景..."
- 用户："他多少钱"
输出 reference_candidates：
[{"target": "基础会员", "attributes": {"price": "68元/月"}, "confidence": 0.95}]

示例 3（无候选）：
用户："有点贵啊"（无对话历史）
输出 reference_candidates：[]
"""
# MARKER: INTENT_PROMPT_END


class IntentService:
    """Calls DeepSeek (via DashScope) to classify user intent.

    All model name, API key and endpoint URL are read from
    ``app.config.Settings`` — nothing is hardcoded.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Public API ────────────────────────────────────────
    async def recognize(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
        trace_id: str | None = None,
    ) -> IntentResult:
        """Classify *query* intent, resolving coreferences from *history*.

        Parameters
        ----------
        query : str
            The user's latest message.
        history : list[dict] | None
            Previous turns, each ``{"role": "user"|"assistant", "content": "..."}``.
        trace_id : str | None
            Shared trace id for correlating all nodes in the chat pipeline.
            If omitted, a new one is generated.

        Returns
        -------
        IntentResult
            Structured result with ``intent``, ``confidence``,
            ``resolved_question`` and ``reason``.
        """
        trace_id = trace_id or uuid.uuid4().hex
        history = history or []
        start_ts = time.perf_counter()

        input_data: dict[str, Any] = {"query": query, "history": history}
        result: IntentResult
        status = "ok"

        try:
            raw_response = await self._call_deepseek(query, history)
            result = self._parse_response(raw_response, query)
        except Exception as exc:
            # ── Degradation: fall back to CHAT, never crash ──
            logger.warning("Intent recognition failed, degrading to CHAT: %s", exc)
            result = IntentResult(
                intent=INTENT_CHAT,
                confidence=0.0,
                resolved_question=query,
                reason=f"Degrade: {type(exc).__name__}: {exc}",
            )
            status = "error"

        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        # ── Fire-and-forget logging (non-blocking) ──────────
        try:
            log_node(
                trace_id=trace_id,
                node="intent_recognition",
                input_data=input_data,
                output_data=result.to_dict(),
                duration_ms=duration_ms,
                service="intent",
                status=status,
            )
        except Exception as log_exc:
            # log_node itself is fail-silent, but guard anyway
            logger.warning("log_node scheduling failed: %s", log_exc)

        return result

    # ── DeepSeek API call ─────────────────────────────────
    async def _call_deepseek(
        self,
        query: str,
        history: list[dict[str, str]],
    ) -> str:
        """Send the chat-completion request and return the raw text content.

        Uses the DashScope compatible-mode endpoint (NOT api.deepseek.com).
        """
        s = self._settings

        messages: list[dict[str, str]] = [{
            "role": "system",
            "content": load_prompt("intent"),
        }]

        # Append conversation history for coreference resolution
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})

        payload: dict[str, Any] = {
            "model": s.deepseek_model,
            "messages": messages,
            "temperature": 0.1,  # low temperature for deterministic classification
            "max_tokens": 512,
        }

        headers = {
            "Authorization": f"Bearer {s.dashscope_api_key}",
            "Content-Type": "application/json",
        }

        url = f"{s.deepseek_base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Extract the assistant's text
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("DeepSeek returned no choices")
        return choices[0]["message"]["content"]

    # ── Response parser ────────────────────────────────────
    @staticmethod
    def _parse_response(raw: str, original_query: str) -> IntentResult:
        """Parse the JSON returned by the model.

        Handles common quirks:
          • Extra markdown fences (```json ... ```)
          • Leading/trailing whitespace or prose
          • Missing fields (filled with defaults)
        """
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            # Remove first line (```json or ```) and last line (```)
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Try to find the JSON object
        # If the model added extra text, extract the { ... } portion
        json_start = text.find("{")
        json_end = text.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start : json_end + 1]

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Failed to parse model response as JSON: {exc}") from exc

        intent = data.get("intent", INTENT_CHAT).upper()
        if intent not in _VALID_INTENTS:
            intent = INTENT_CHAT

        confidence = data.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            confidence = 0.0

        resolved = data.get("resolved_question") or original_query
        reason = data.get("reason") or ""
        related = data.get("related_sections")
        if not isinstance(related, list):
            related = None

        # 多目标指代候选：list[{"target": str, "attributes": dict, "confidence": float}]
        # 向后兼容：LLM 未输出时保持 None，格式异常时置 None 不报错
        reference_candidates = data.get("reference_candidates")
        if isinstance(reference_candidates, list):
            cleaned: list[dict] = []
            for cand in reference_candidates:
                if not isinstance(cand, dict):
                    continue
                entry: dict = {}
                if isinstance(cand.get("target"), str):
                    entry["target"] = cand["target"]
                if isinstance(cand.get("attributes"), dict):
                    entry["attributes"] = cand["attributes"]
                conf = cand.get("confidence")
                if isinstance(conf, (int, float)) and 0 <= conf <= 1:
                    entry["confidence"] = float(conf)
                if entry:
                    cleaned.append(entry)
            reference_candidates = cleaned or None
        else:
            reference_candidates = None

        return IntentResult(
            intent=intent,
            confidence=float(confidence),
            resolved_question=str(resolved),
            reason=str(reason),
            related_sections=related,
            reference_candidates=reference_candidates,
        )
