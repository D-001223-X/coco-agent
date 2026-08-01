"""Chat router — full pipeline: session → history → intent → retrieve/rerank → LLM → persist.

All business logic is delegated to service-layer classes; the router
only orchestrates and handles HTTP concerns (auth, serialisation, errors).
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import Message, Session, User
from app.routers.auth import get_current_user
from app.services.intent_service import INTENT_CHAT, INTENT_FEEDBACK, INTENT_SUPPORT, IntentService
from app.services.llm_service import LLMService
from app.services.rerank_service import RerankService
from app.services.retrieval_service import RetrievedChunk
from app.utils.logger import log_node
from app.services.admin.param_service import get_retrieval_service

router = APIRouter(prefix="/api", tags=["chat"])

_KB_INTENTS = {INTENT_SUPPORT, INTENT_FEEDBACK}

# ── Singleton services (lazy, safe to reuse) ─────────────
_intent_service = IntentService()
_retrieval_service = get_retrieval_service()  # shared with admin param tuning
_rerank_service = RerankService()
_llm_service = LLMService()


# ── Schemas ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ResponseContent(BaseModel):
    useful: bool
    content: str


class ChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    message_id: int
    response: ResponseContent
    intent: str
    resolved_question: str


# ── Error response ──────────────────────────────────────
class ErrorResponse(BaseModel):
    code: int
    data: None = None
    msg: str


# ── Route ────────────────────────────────────────────────
@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def chat(
    request: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Full AI customer-service pipeline.

    1. Session management (create or validate)
    2. Fetch conversation history
    3. Intent recognition
    4. Route: CHAT → LLM; SUPPORT/FEEDBACK → retrieve → rerank → LLM
    5. Persist messages
    6. Return response
    """
    trace_id = uuid.uuid4().hex
    s = get_settings()

    try:
        # ── 1. Session management ────────────────────────────
        session_id = request.session_id
        if session_id is None:
            # Create new session
            session_id = uuid.uuid4().hex
            current_session = Session(id=session_id, user_id=current_user.id)
            db.add(current_session)
            await db.commit()
        else:
            # Validate existing session belongs to current user
            result = await db.execute(
                select(Session).where(
                    Session.id == session_id,
                    Session.user_id == current_user.id,
                )
            )
            current_session = result.scalar_one_or_none()
            if current_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

        # ── 2. Fetch history (last 10 messages, chronologically) ──
        history_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .limit(10)
        )
        db_messages = history_result.scalars().all()
        history = [
            {"role": m.role, "content": m.content}
            for m in db_messages
        ]

        # ── 3. Intent recognition ──────────────────────────────
        intent_result = await _intent_service.recognize(
            request.message, history, trace_id=trace_id,
        )

        # ── 4. Route ─────────────────────────────────────────
        llm_input_chunks: list[RetrievedChunk] = []
        llm_intent = intent_result.intent

        if intent_result.intent in _KB_INTENTS:
            # SUPPORT / FEEDBACK: retrieve → rerank
            # 章节限定检索：若意图识别输出 related_sections，仅在该章节内检索
            # FEEDBACK 使用更宽松的检索参数（阈值更低，确保能召回相关知识）
            is_feedback = intent_result.intent == "FEEDBACK"
            retrieved = await _retrieval_service.search(
                intent_result.resolved_question,
                top_k=3 if is_feedback else s.top_k,
                threshold=0.15 if is_feedback else s.score_threshold,
                trace_id=trace_id,
                sections=intent_result.related_sections,
            )
            if retrieved:
                doc_texts = [c.content for c in retrieved]
                reranked = await _rerank_service.rerank(
                    intent_result.resolved_question, doc_texts, top_k=3,
                    trace_id=trace_id,
                )
                # Map reranked docs back to RetrievedChunk objects
                doc_to_chunk = {c.content: c for c in retrieved}
                llm_input_chunks = []
                for doc, score in reranked:
                    if doc in doc_to_chunk:
                        chunk = doc_to_chunk[doc]
                        # Update score to rerank score
                        chunk.score = score
                        llm_input_chunks.append(chunk)

        # Generate LLM response
        llm_result = await _llm_service.generate(
            query=intent_result.resolved_question,
            history=history,
            chunks=llm_input_chunks,
            intent=llm_intent,
            trace_id=trace_id,
            reference_candidates=intent_result.reference_candidates,
        )

        # ── 5. Persist messages ──────────────────────────────
        # User message
        user_msg = Message(
            session_id=session_id,
            role="user",
            content=request.message,
        )
        db.add(user_msg)
        await db.flush()

        # Touch session updated_at
        current_session.updated_at = datetime.now(timezone.utc)

        # Assistant response
        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content=llm_result.get("content", ""),
        )
        db.add(assistant_msg)
        await db.flush()

        await db.commit()

        # ── 6. Return response ──────────────────────────────
        return ChatResponse(
            session_id=session_id,
            message_id=assistant_msg.id,
            response=ResponseContent(
                useful=llm_result.get("useful", False),
                content=llm_result.get("content", ""),
            ),
            intent=intent_result.intent,
            resolved_question=intent_result.resolved_question,
        )

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions as-is
        raise
    except Exception as exc:
        # Catch-all: never leak internal details
        log_node(
            trace_id=trace_id,
            node="chat_pipeline",
            input_data={
                "session_id": request.session_id,
                "message_preview": request.message[:100],
            },
            output_data={"error": type(exc).__name__},
            duration_ms=0,
            service="chat",
            status="error",
            user_id=current_user.id,
            session_id=request.session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
