"""陪练会话管理 API（T-004）。

GET  /api/practice/modes             — 获取可用模式和场景
POST /api/practice/session/start    — 开始新会话
POST /api/practice/session/chat     — 发送消息
POST /api/practice/session/end      — 结束会话
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.models import User
from app.routers.auth import get_current_user
from app.services.practice.session_service import SessionService
from app.agent.skills import get_available_modes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice", tags=["practice-session"])

UserDep = Annotated[User, Depends(get_current_user)]

_session_service = SessionService()


class StartSessionRequest(BaseModel):
    mode: str
    scenario: str = ""
    userLevel: str = "A2"
    userId: str = "user_001"


class ChatRequest(BaseModel):
    sessionId: str
    message: str


class EndSessionRequest(BaseModel):
    sessionId: str


@router.get("/modes")
async def get_modes(_user: UserDep):
    """返回可用陪练模式及场景列表。"""
    return {"code": 0, "data": {"modes": get_available_modes()}, "msg": "success"}


@router.post("/session/start")
async def start_session(req: StartSessionRequest, _user: UserDep):
    """开始新的陪练会话。"""
    try:
        session, greeting = _session_service.start_session(
            mode=req.mode,
            scenario=req.scenario,
            user_level=req.userLevel,
            user_id=req.userId,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "code": 0,
        "data": {"sessionId": session.session_id, "agentGreeting": greeting},
        "msg": "success",
    }


@router.post("/session/chat")
async def chat(req: ChatRequest, _user: UserDep):
    """处理用户消息。"""
    try:
        result = await _session_service.chat(req.sessionId, req.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "code": 0,
        "data": {
            "reply": result["reply"],
            "correction": result.get("correction"),
            "agentThought": result.get("agentThought"),
            "decision": result.get("decision"),
            "roundId": result.get("roundId"),
        },
        "msg": "success",
    }


@router.post("/session/end")
async def end_session(req: EndSessionRequest, _user: UserDep):
    """结束会话。"""
    session = _session_service.end_session(req.sessionId)
    return {
        "code": 0,
        "data": {"sessionId": req.sessionId, "ended": session is not None},
        "msg": "success",
    }
