"""学习进度 API（T-006）。

GET  /api/practice/progress             — 获取用户学习进度
POST /api/practice/progress/feedback    — 生成智能反馈报告
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_current_user
from app.services.practice.feedback_service import FeedbackService
from app.services.practice.progress_service import ProgressService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice/progress", tags=["practice-progress"])

UserDep = Annotated[User, Depends(get_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

_progress_service = ProgressService()
_feedback_service = FeedbackService()


class FeedbackRequest(BaseModel):
    userId: str = "user_001"
    userLevel: str = "A2"


@router.get("")
async def get_progress(_user: UserDep, db: DbDep):
    """获取用户学习进度统计。"""
    user_id = str(_user.id)
    try:
        records = await _progress_service.load_records(db, user_id)
        progress = _progress_service.calculate_progress(user_id, records)
        return {"code": 0, "data": progress, "msg": "success"}
    except Exception as exc:
        logger.error("get_progress failed: %s", exc)
        return {"code": 500, "data": None, "msg": f"获取进度失败: {exc}"}


@router.post("/feedback")
async def generate_feedback(req: FeedbackRequest, _user: UserDep, db: DbDep):
    """基于进度数据生成智能反馈。"""
    try:
        records = await _progress_service.load_records(db, req.userId)
        progress = _progress_service.calculate_progress(req.userId, records)
        feedback = await _feedback_service.generate_feedback(
            progress, req.userLevel
        )
        return {"code": 0, "data": {"feedback": feedback}, "msg": "success"}
    except Exception as exc:
        logger.error("generate_feedback failed: %s", exc)
        return {"code": 500, "data": None, "msg": f"反馈生成失败: {exc}"}
