"""LLM response generation service — branches on intent, uses DeepSeek via DashScope.

Architecture:
  • CHAT intent: friendly casual reply, never passes knowledge chunks.
  • SUPPORT / FEEDBACK intent: knowledge-grounded reply with English translation.
  • Empty chunks → refuse to answer (no hallucination).
  • Degrades gracefully: missing API key → mock mode; timeout/error → fallback.
  • Strict character-limit enforcement with truncation + "…".
  • Every call is logged via ``log_node`` (fire-and-forget, non-blocking).
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import httpx

from app.config import get_settings
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

# ── Fallback / refusal replies (never translated) ──────────
_FALLBACK_REPLY = {
    "useful": False,
    "content": "服务繁忙，请稍后再试",
    "translation": "Service busy, please try again later.",
}

_REFUSE_REPLY = {
    "useful": False,
    "content": "暂时不能回答这个问题",
    "translation": "I cannot answer this question for now.",
}

# ── System prompts (admin-editable via markers) ───────────
# MARKER: SUPPORT_PROMPT_START
SUPPORT_SYSTEM_PROMPT = """\
你是可可语伴产品客服助手。请基于以下知识内容，用中文回答用户的问题，回答需简洁、准确，控制在100字以内。

如果检索到的知识片段与用户问题明显不相关（如分数低于阈值），即使存在片段，也应视为“未找到相关知识”，返回useful=false，拒绝回答。

知识内容：
{context}
"""
# MARKER: SUPPORT_PROMPT_END

# MARKER: CHAT_PROMPT_START
CHAT_SYSTEM_PROMPT = """\
你是可可语伴的AI助手。请用友好、轻松的语气回复用户，回复内容控制在50字以内，无需翻译。
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
    ) -> dict[str, Any]:
        """Generate a response based on *intent*, *chunks* and *query*.

        Parameters
        ----------
        trace_id : str | None
            Shared trace id for correlating all nodes in the chat pipeline.

        Returns
        -------
        dict
            ``{"useful": bool, "content": str, "translation": str}``
        """
        trace_id = trace_id or uuid.uuid4().hex
        start_ts = time.perf_counter()
        status = "ok"

        # Determine which service handled the request for logging
        service_name = "DeepSeek"

        try:
            result = await self._route(query, history, chunks, intent)
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
                    "content_preview": result.get("content", "")[:50],
                },
                duration_ms=duration_ms,
                service=service_name,
                status=status,
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
    ) -> dict[str, Any]:
        """Route to appropriate handler based on intent."""

        # SUPPORT / FEEDBACK with empty chunks: refuse (never call LLM)
        if intent in _KB_INTENTS and not chunks:
            return dict(_REFUSE_REPLY)

        # CHAT
        if intent == INTENT_CHAT:
            return await self._handle_chat(query, history)

        # SUPPORT / FEEDBACK with chunks
        return await self._handle_knowledge(query, chunks)

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
                "translation": "",
            }

        system_prompt = load_prompt("chat")

        raw = await self._call_deepseek(query, history, system_prompt)
        content = self._truncate(raw, 50)
        return {
            "useful": True,
            "content": content,
            "translation": "",
        }

    # ── SUPPORT / FEEDBACK handler ──────────────────────────
    async def _handle_knowledge(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> dict[str, Any]:
        """Knowledge-based answer with translation."""
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
                "translation": "",
            }

        base_prompt = load_prompt("support")
        system_prompt = base_prompt.format(context=context)

        raw = await self._call_deepseek(query, [], system_prompt)

        # Split content and translation (first line = content, rest = translation)
        parts = raw.strip().split("\n", 1)
        content = self._truncate(parts[0].strip(), 100)
        translation = parts[1].strip() if len(parts) > 1 else ""

        return {
            "useful": True,
            "content": content,
            "translation": translation,
        }

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
