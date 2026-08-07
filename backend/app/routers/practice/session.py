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

from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from app.services.practice.session_service import SessionService
from app.agent.skills import get_available_modes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice", tags=["practice-session"])

DbDep = Annotated[AsyncSession, Depends(get_db)]

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


class SwitchScenarioRequest(BaseModel):
    sessionId: str
    scenario: str


@router.get("/modes")
async def get_modes():
    """返回可用陪练模式及场景列表。"""
    return {"code": 0, "data": {"modes": get_available_modes()}, "msg": "success"}


@router.post("/session/start")
async def start_session(req: StartSessionRequest, db: DbDep):
    """开始新的陪练会话（P0：落库保证多实例可见）。"""
    try:
        session, greeting = await _session_service.start_session(
            mode=req.mode,
            scenario=req.scenario,
            user_level=req.userLevel,
            user_id=req.userId,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "code": 0,
        "data": {"sessionId": session.session_id, "agentGreeting": greeting},
        "msg": "success",
    }


@router.post("/session/chat")
async def chat(req: ChatRequest, db: DbDep):
    """处理用户消息（P0：每轮落库，跨实例可恢复）。"""
    try:
        result = await _session_service.chat(req.sessionId, req.message, db=db)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "code": 0,
        "data": {
            "reply": result["reply"],
            "correction": result.get("correction"),
            "agentThought": result.get("agentThought"),
            "react_loop": result.get("react_loop"),
            "naturalSummary": result.get("naturalSummary"),
            "decision": result.get("decision"),
            "roundId": result.get("roundId"),
        },
        "msg": "success",
    }


@router.post("/session/end")
async def end_session(req: EndSessionRequest, db: DbDep):
    """结束会话并持久化记录。"""
    try:
        session = await _session_service.end_session_async(req.sessionId, db=db)
    except Exception as exc:  # noqa: BLE001
        # 诊断：透传异常类型便于线上定位（不泄露堆栈）
        raise HTTPException(status_code=500, detail=f"end failed ({type(exc).__name__}: {exc})") from exc
    return {
        "code": 0,
        "data": {"sessionId": req.sessionId, "ended": session is not None},
        "msg": "success",
    }


@router.post("/session/switch")
async def switch_scenario(req: SwitchScenarioRequest, db: DbDep):
    """切换会话的场景/话题（保留历史上下文，T-005）。"""
    try:
        session, new_greeting = await _session_service.switch_scenario(
            req.sessionId, req.scenario, db=db
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        # 诊断：透传异常类型便于线上定位（不泄露堆栈）
        raise HTTPException(status_code=500, detail=f"switch failed ({type(exc).__name__}: {exc})") from exc

    return {
        "code": 0,
        "data": {
            "sessionId": session.session_id,
            "scenario": session.scenario,
            "agentGreeting": new_greeting,
        },
        "msg": "success",
    }
