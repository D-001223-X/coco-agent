"""学习进度 API（T-006）。

GET  /api/practice/progress             — 获取用户学习进度
POST /api/practice/progress/feedback    — 生成智能反馈报告
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.routers.auth import get_optional_current_user
from app.services.practice.feedback_service import FeedbackService
from app.services.practice.progress_service import ProgressService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice/progress", tags=["practice-progress"])

# 访客模式：可选认证（有 token 用登录用户，无 token 为访客）
OptUserDep = Annotated[User | None, Depends(get_optional_current_user)]
DbDep = Annotated[AsyncSession, Depends(get_db)]

_progress_service = ProgressService()
_feedback_service = FeedbackService()


class FeedbackRequest(BaseModel):
    # 兼容旧请求体；实际以登录用户为准（与 GET /progress 数据源统一）
    userId: str | None = None
    userLevel: str = "A2"


@router.get("")
async def get_progress(
    user: OptUserDep,
    db: DbDep,
    x_device_id: Annotated[str | None, Header(alias="X-Device-ID")] = None,
):
    """获取学习进度统计。

    - 登录用户：按 user.id 查记录
    - 访客：按 X-Device-ID（设备）查记录（P2：进度按设备隔离统计）
    - 无身份：完整空结构
    """
    # 访客：按设备查 records 计算真实进度
    if user is None:
        device_id = (x_device_id or "").strip()
        if device_id:
            try:
                records = await _progress_service.load_records(db, device_id)
                progress = _progress_service.calculate_progress(device_id, records)
                return {"code": 0, "data": progress, "msg": "success"}
            except Exception as exc:
                logger.error("get_progress(guest) failed: %s", exc)
                return {"code": 500, "data": None, "msg": f"获取进度失败: {exc}"}
        empty = {
            "userId": "guest",
            "totalDays": 0,
            "totalSessions": 0,
            "totalRounds": 0,
            "totalCorrections": 0,
            "strengths": ["暂无高频错误记录"],
            "weaknesses": [],
            "errorPatterns": {"grammar": 0, "vocabulary": 0, "pronunciation": 0},
            "errorExamples": [],
            "dailyLogs": [],
            "activeDays7": 0,
            "activeDays30": 0,
            "updatedAt": None,
        }
        return {"code": 0, "data": empty, "msg": "success"}
    user_id = str(user.id)
    try:
        records = await _progress_service.load_records(db, user_id)
        progress = _progress_service.calculate_progress(user_id, records)
        return {"code": 0, "data": progress, "msg": "success"}
    except Exception as exc:
        logger.error("get_progress failed: %s", exc)
        return {"code": 500, "data": None, "msg": f"获取进度失败: {exc}"}


@router.post("/feedback")
async def generate_feedback(req: FeedbackRequest, user: OptUserDep, db: DbDep):
    """基于进度数据生成智能反馈（访客 → 返回默认提示）。"""
    if user is None:
        return {"code": 0, "data": {"feedback": "完成一次陪练后，我将为你生成学习反馈～"}, "msg": "success"}
    try:
        user_id = str(user.id)
        records = await _progress_service.load_records(db, user_id)
        progress = _progress_service.calculate_progress(user_id, records)
        feedback = await _feedback_service.generate_feedback(
            progress, req.userLevel
        )
        return {"code": 0, "data": {"feedback": feedback}, "msg": "success"}
    except Exception as exc:
        logger.error("generate_feedback failed: %s", exc)
        return {"code": 500, "data": None, "msg": f"反馈生成失败: {exc}"}
