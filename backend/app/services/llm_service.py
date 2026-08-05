"""LLM response generation service — branches on intent, uses DeepSeek via DashScope.

Architecture:
  • CHAT intent: friendly casual reply, never passes knowledge chunks.
  • SUPPORT intent: knowledge-grounded reply.
  • FEEDBACK intent: feedback response via dedicated prompt.
  • Empty chunks → refuse to answer (no hallucination).
  • Degrades gracefully: missing API key → mock mode; timeout/error → fallback.
  • Strict character-limit enforcement with truncation + "…".
  • Every call is logged via ``log_node`` (fire-and-forget, non-blocking).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

import httpx

from app.config import get_settings
from app.services.admin.config_service import get_config_value
from app.services.admin.prompt_service import load_prompt
from app.services.retrieval_service import RetrievedChunk
from app.utils.logger import log_node

logger = logging.getLogger(__name__)

# ── Intents ──────────────────────────────────────────────
INTENT_CHAT = "CHAT"
INTENT_SUPPORT = "SUPPORT"
INTENT_FEEDBACK = "FEEDBACK"
_KB_INTENTS = {INTENT_SUPPORT, INTENT_FEEDBACK}

# ── Mock chat reply (used when DASHSCOPE_API_KEY is empty) ─
_MOCK_CHAT_REPLY = "你好呀，我是可可语伴的AI助手~"

# ── Fallback / refusal replies ─────────────────────────────
_FALLBACK_REPLY = {
    "useful": False,
    "content": "服务繁忙，请稍后再试",
}

_REFUSE_REPLY = {
    "useful": False,
    "content": "暂时不能回答这个问题",
}

# ── System prompts (admin-editable via markers) ───────────
# MARKER: SUPPORT_PROMPT_START
SUPPORT_SYSTEM_PROMPT = """\
你是可可语伴产品客服助手。基于提供的知识内容回答用户的问题。

回答要求：
1. 直接基于知识内容回答，不要使用外部知识
2. 回答简洁、准确，控制在 150 字以内
3. 回答时，如果用户问题包含“他”、“这个”等代词，优先从最近 3 轮对话中查找指代对象。 
4. 如果用户问题无法通过知识内容回答，回答："这个问题我暂时无法回答"

【可能的指代对象】
{candidates}

【指代回答规则】
1. 如果候选对象有多个（如基础会员和大会员），必须分别解释每个对象的价值（价格、权益、适用人群），避免只覆盖其中一个
2. 如果只有一个候选对象，针对该对象解释性价比
3. 如果没有候选对象（无明确指代），正常基于知识内容回答

【知识内容】
{context}
"""
# MARKER: SUPPORT_PROMPT_END

# MARKER: CHAT_PROMPT_START
CHAT_SYSTEM_PROMPT = """\
你是可可语伴的AI助手，擅长陪伴用户进行轻松、温暖的闲聊。你的核心任务是与用户建立自然、信任的关系，并在对话中自然地传递产品价值。

## 对话风格
- 亲切、自然，像朋友聊天一样
- 避免推销感，注重倾听和共鸣
- 根据用户回答灵活调整，不强行推进问题
- 当用户主动询问产品时，用口语化的例子或场景说明产品价值

## 引导反馈（仅在用户表现出交流意愿时使用）
- 不主动追问所有问题，只在用户表现出兴趣时顺势引导
- 以下问题可作为引导方向，但不要在一次对话中全部抛出：
  1. 你是怎么了解到我们产品的呀？
  2. 最近使用起来感觉怎么样？有没有特别喜欢的部分？
  3. 如果让你提一个建议，你会希望我们改进什么？

## 禁止事项
1. 不要虚构实时信息（天气、新闻、股票等）
2. 不要假装具备查询外部数据的能力
3. 如果用户询问实时信息，诚实告知无法获取，并建议其他渠道

## 输入信息
{query}

## 输出要求
1. 用中文回复，不超过 100 字
2. 直接输出纯文本内容，不要输出 JSON 或其他格式
"""
# MARKER: CHAT_PROMPT_END


class LLMService:
    """Generate answers using DeepSeek (via DashScope) with intent-based branching."""

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Public API ─────────────────────────────────────────
    async def generate(
        self,
        query: str,
        history: list[dict[str, str]],
        chunks: list[RetrievedChunk],
        intent: str,
        trace_id: str | None = None,
        reference_candidates: list[dict] | None = None,
        device_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a response based on *intent*, *chunks* and *query*.

        Parameters
        ----------
        trace_id : str | None
            Shared trace id for correlating all nodes in the chat pipeline.
        reference_candidates : list[dict] | None
            Candidate reference objects (from intent recognition) used to
            explain each possible referent when multiple are ambiguous.

        Returns
        -------
        dict
            ``{"useful": bool, "content": str}``
        """
        trace_id = trace_id or uuid.uuid4().hex
        start_ts = time.perf_counter()
        status = "ok"

        # Determine which service handled the request for logging
        service_name = "DeepSeek"

        try:
            result = await self._route(
                query, history, chunks, intent, reference_candidates
            )
            # If we hit mock mode, the service is "Mock"
            if not self._settings.dashscope_api_key:
                service_name = "Mock"
        except Exception as exc:
            logger.warning("LLM generate failed, returning fallback: %s", exc)
            result = dict(_FALLBACK_REPLY)
            status = "error"

        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        try:
            log_node(
                trace_id=trace_id,
                node="llm_generate",
                input_data={
                    "query": query,
                    "intent": intent,
                    "chunk_count": len(chunks),
                },
                output_data={
                    "useful": result.get("useful", False),
                    "content": result.get("content", ""),
                    "content_preview": result.get("content", "")[:50],
                },
                duration_ms=duration_ms,
                service=service_name,
                status=status,
                device_id=device_id,
            )
        except Exception as log_exc:
            logger.warning("log_node scheduling failed: %s", log_exc)

        # ── Data flywheel: auto-collect bad cases (useful=false) ──
        if not result.get("useful", False):
            try:
                await self._record_bad_case(
                    trace_id=trace_id,
                    query=query,
                    answer=result.get("content", ""),
                    intent=intent,
                )
            except Exception as exc:
                logger.warning("Bad-case auto-collect failed: %s", exc)

        return result

    # ── Refusal phrase from config (async, DB-backed) ──────
    async def _get_refuse_phrase(self) -> str:
        """Load the 'refuse_uncovered' phrase from system config (DB)."""
        try:
            from sqlalchemy import select

            from app.database import get_session_factory
            from app.models import SystemConfig

            factory = get_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(SystemConfig.value).where(SystemConfig.key == "refuse_uncovered")
                )
                value = result.scalar_one_or_none()
                if value:
                    return value
        except Exception:
            pass
        return "暂时不能回答这个问题"

    # ── Data flywheel: auto-record bad case ────────────────
    async def _record_bad_case(
        self,
        trace_id: str,
        query: str,
        answer: str,
        intent: str,
    ) -> None:
        """Insert a BadCase row when the answer was not useful (idempotent)."""
        try:
            from sqlalchemy import select

            from app.database import get_session_factory
            from app.models import BadCase

            factory = get_session_factory()
            async with factory() as session:
                exists = await session.execute(
                    select(BadCase.id).where(BadCase.trace_id == trace_id)
                )
                if exists.scalar_one_or_none() is not None:
                    return
                session.add(BadCase(
                    trace_id=trace_id,
                    user_question=query,
                    system_answer=answer,
                    intent=intent,
                    source="auto",
                    status="pending",
                ))
                await session.commit()
                logger.info("Bad case auto-recorded: trace=%s", trace_id)
        except Exception as exc:
            logger.warning("Bad-case insert failed: %s", exc)

    # ── Internal: routing by intent ────────────────────────
    async def _route(
        self,
        query: str,
        history: list[dict[str, str]],
        chunks: list[RetrievedChunk],
        intent: str,
        reference_candidates: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Route to appropriate handler based on intent."""

        # SUPPORT / FEEDBACK with empty chunks: refuse (never call LLM)
        if intent in _KB_INTENTS and not chunks:
            refuse_content = await self._get_refuse_phrase()
            return {
                "useful": False,
                "content": refuse_content,
            }

        # CHAT
        if intent == INTENT_CHAT:
            return await self._handle_chat(query, history)

        # FEEDBACK with chunks → dedicated feedback handler
        if intent == INTENT_FEEDBACK:
            return await self._handle_feedback(
                query, chunks, reference_candidates
            )

        # SUPPORT with chunks
        return await self._handle_knowledge(query, chunks, reference_candidates)

    # ── CHAT handler ──────────────────────────────────────
    async def _handle_chat(
        self,
        query: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Friendly chat — no knowledge chunks involved."""
        s = self._settings

        # Mock mode: no API key
        if not s.dashscope_api_key:
            return {
                "useful": True,
                "content": _MOCK_CHAT_REPLY,
            }

        system_prompt = load_prompt("chat")

        raw = await self._call_deepseek(query, history, system_prompt)
        # 防御性解析 + 放宽兜底到 800 字：字数由提示词控制，不硬编码截断
        content = self._extract_json_content(raw, max_chars=800)
        return {
            "useful": True,
            "content": content,
        }

    # ── SUPPORT / FEEDBACK handler ──────────────────────────
    async def _handle_knowledge(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        reference_candidates: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Knowledge-based answer."""
        s = self._settings

        # Build context from chunks
        context = "\n---\n".join(c.content for c in chunks)

        # Mock mode: use first chunk content
        if not s.dashscope_api_key:
            first_chunk = chunks[0].content
            truncated = self._truncate(first_chunk, 100)
            return {
                "useful": True,
                "content": truncated,
            }

        candidates_text = self._format_candidates(reference_candidates)
        base_prompt = load_prompt("support")
        system_prompt = self._fill_prompt(
            base_prompt, query=query, context=context, candidates=candidates_text
        )

        raw = await self._call_deepseek(query, [], system_prompt)

        # 防御性解析（JSON 解包 / 纯文本兜底）。上限放宽到 800 字，
        # 实际长度由提示词控制——硬编码截断会砍掉 LLM 的完整回答。
        content = self._extract_json_content(raw, max_chars=800)

        return {
            "useful": True,
            "content": content,
        }

    # ── FEEDBACK handler ──────────────────────────────────
    async def _handle_feedback(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        reference_candidates: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Handle FEEDBACK intent: judge whether the suggestion is covered by KB."""
        s = self._settings

        # Mock mode: no API key → generic acknowledgement
        if not s.dashscope_api_key:
            return {
                "useful": True,
                "content": "感谢您的反馈，我们会认真考虑。",
            }

        context = "\n---\n".join(c.content for c in chunks)
        candidates_text = self._format_candidates(reference_candidates)
        base_prompt = load_prompt("feedback")
        system_prompt = self._fill_prompt(
            base_prompt, query=query, context=context, candidates=candidates_text
        )

        raw = await self._call_deepseek(query, [], system_prompt)

        # The model is instructed to reply as JSON {"content": "..."} —
        # parse it, degrade to plain text if parsing fails.
        content = self._extract_json_content(raw, max_chars=800)
        return {
            "useful": True,
            "content": content,
        }

    # ── Prompt helpers ────────────────────────────────────
    @staticmethod
    def _fill_prompt(
        template: str, query: str, context: str, candidates: str | None = None
    ) -> str:
        """Fill a prompt template supporting ``{query}/{context}/{candidates}`` and
        ``%S/%s/%`` placeholder styles (both are used across admin prompts).
        """
        # 1) Python str.format: expands {{ }} escapes and {query}/{context}/{candidates}
        text = template.format(
            query=query, context=context, candidates=candidates or "（无明确指代对象）"
        )
        # 2) Legacy %-style placeholders used by the FEEDBACK prompt:
        text = text.replace("%S", context).replace("%s", query)
        # 3) Bare '%' marker for knowledge section (must run after %S/%s)
        text = text.replace("%", context)
        return text

    @staticmethod
    def _format_candidates(candidates: list[dict] | None) -> str:
        """将 reference_candidates 格式化为 Prompt 可用的文本。

        多候选时逐条列出 target / attributes / confidence，方便 LLM
        分别解释每个对象的价值。
        """
        if not candidates:
            return "（无明确指代对象）"

        lines: list[str] = []
        for idx, cand in enumerate(candidates, 1):
            target = cand.get("target", "未知")
            attrs = cand.get("attributes", {})
            confidence = cand.get("confidence", 0)
            if not isinstance(attrs, dict):
                attrs = {}
            attr_str = "，".join(
                f"{k}: {v}" for k, v in attrs.items() if v is not None
            )
            try:
                conf_pct = f"{float(confidence):.0%}"
            except (TypeError, ValueError):
                conf_pct = "未知"
            line = f"{idx}. {target}"
            if attr_str:
                line += f"（{attr_str}）"
            line += f"，置信度: {conf_pct}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _extract_json_content(raw: str, max_chars: int = 800) -> str:
        """Extract ``content`` from a JSON-wrapped model reply.

        Handles plain text, JSON objects (with/without markdown fences) and
        JSON containing a ``content`` key. Falls back to the raw text.
        """
        text = (raw or "").strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Try JSON parse
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                content = data.get("content")
                if isinstance(content, str) and content.strip():
                    return LLMService._truncate(content.strip(), max_chars)
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: use raw text as-is
        return LLMService._truncate(text, max_chars)

    # ── DeepSeek API call ─────────────────────────────────
    async def _call_deepseek(
        self,
        query: str,
        history: list[dict[str, str]],
        system_prompt: str,
    ) -> str:
        """Send chat-completion request, return the text content."""
        s = self._settings

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
        ]

        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})

        payload: dict[str, Any] = {
            "model": s.deepseek_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2048,
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

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("DeepSeek returned no choices")
        return choices[0]["message"]["content"].strip()

    # ── Truncation guard ──────────────────────────────────
    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Truncate text to *max_chars* characters, add '…' if truncated."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "…"
