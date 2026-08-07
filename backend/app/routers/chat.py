"""Chat router — full pipeline: session → history → intent → retrieve/rerank → LLM → persist.

All business logic is delegated to service-layer classes; the router
only orchestrates and handles HTTP concerns (auth, serialisation, errors).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
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


# ── P-002 设备/用户识别依赖 ──────────────────────────────
class ChatIdentity(BaseModel):
    """已登录用户 或 访客（X-Device-ID 标识）。"""
    user_id: int | None = None
    email: str | None = None
    is_guest: bool = True
    device_id: str | None = None


async def get_chat_identity(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_device_id: Annotated[str | None, Header()] = None,
) -> ChatIdentity:
    """优先用 JWT 识别用户；无 token 时用 X-Device-ID 作为访客标识。"""
    # 尝试解析 Bearer token（失败不阻塞访客）
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            from jose import jwt as jose_jwt
            s = get_settings()
            payload = jose_jwt.decode(
                auth[7:].strip(), s.secret_key, algorithms=[s.algorithm]
            )
            email = payload.get("sub")
            if email:
                result = await db.execute(
                    select(User).where(User.email == email)
                )
                user = result.scalar_one_or_none()
                if user is not None:
                    return ChatIdentity(
                        user_id=user.id,
                        email=user.email,
                        is_guest=False,
                        device_id=None,
                    )
        except Exception:
            pass  # token 无效 → 降级访客

    # 访客：需 X-Device-ID（前端必带）
    device_id = (x_device_id or "").strip()
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Device-ID for guest access",
        )
    return ChatIdentity(is_guest=True, device_id=device_id)


ChatIdentityDep = Annotated[ChatIdentity, Depends(get_chat_identity)]


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
    identity: ChatIdentityDep,
    db: AsyncSession = Depends(get_db),
):
    """Full AI customer-service pipeline.

    1. Session management (create or validate; 访客用 device_id 隔离)
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
            # Create new session（登录用户 user_id；访客 device_id）
            session_id = uuid.uuid4().hex
            current_session = Session(
                id=session_id,
                user_id=identity.user_id if not identity.is_guest else None,
                device_id=identity.device_id,
            )
            db.add(current_session)
            await db.commit()
        else:
            # Validate existing session belongs to current user / device
            result = await db.execute(
                select(Session).where(Session.id == session_id)
            )
            current_session = result.scalar_one_or_none()
            if current_session is None:
                raise HTTPException(status_code=404, detail="Session not found")
            # 归属校验：登录用户校验 user_id；访客校验 device_id
            if identity.is_guest:
                if current_session.device_id != identity.device_id:
                    raise HTTPException(status_code=404, detail="Session not found")
            else:
                if current_session.user_id != identity.user_id:
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
            request.message, history, trace_id=trace_id, device_id=identity.device_id,
        )

        # ── 4. Route ─────────────────────────────────────────
        llm_input_chunks: list[RetrievedChunk] = []
        llm_intent = intent_result.intent

        if intent_result.intent in _KB_INTENTS:
            # 索引未就绪（冷启动重建中）→ 友好提示，避免空拒答
            if not _retrieval_service.is_index_ready():
                logger.warning(
                    "[chat] KB index not ready yet (cold start) → friendly hint, trace=%s",
                    trace_id,
                )
                return {
                    "code": 0,
                    "data": {
                        "message": "系统正在初始化知识库，请稍等几秒再问我一次哦～",
                        "intent": intent_result.intent,
                        "trace_id": trace_id,
                        "reactions": [],
                    },
                    "msg": "success",
                }

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
                device_id=identity.device_id,
            )
            if retrieved:
                doc_texts = [c.content for c in retrieved]
                reranked = await _rerank_service.rerank(
                    intent_result.resolved_question, doc_texts, top_k=3,
                    trace_id=trace_id, device_id=identity.device_id,
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
            device_id=identity.device_id,
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

        # Session updated_at 由模型 onupdate=func.now() 自动刷新
        # （与 created_at 同源，避免 UTC/本地混用导致前端差 8 小时）

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
        # Catch-all: 记录错误类型到日志与响应（不泄露堆栈），便于线上定位
        log_node(
            trace_id=trace_id,
            node="chat_pipeline",
            input_data={
                "session_id": request.session_id,
                "message_preview": request.message[:100],
            },
            output_data={"error": f"{type(exc).__name__}: {exc}"},
            duration_ms=0,
            service="chat",
            status="error",
            user_id=identity.user_id if identity.user_id is not None else 0,
            session_id=request.session_id,
            device_id=identity.device_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error ({type(exc).__name__}: {str(exc)[:200]})",
        )
