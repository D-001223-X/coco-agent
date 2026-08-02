"""学习进度计算服务（T-006）。

从已结束的陪练会话记录中统计学习数据：
  - 总天数 / 会话数 / 对话轮次 / 纠正次数
  - 错误类型分布（grammar/vocabulary/pronunciation）+ 示例
  - 薄弱环节识别
  - 每日活跃日志（近 7/30 天）
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PracticeSessionRecord

logger = logging.getLogger(__name__)

_ERROR_LABELS = {
    "grammar": "语法",
    "vocabulary": "词汇",
    "pronunciation": "发音",
}

# LLM 可能输出的其他纠错类型 → 归一到三类
_ERROR_NORMALIZE = {
    "grammar": "grammar",
    "syntax": "grammar",
    "tense": "grammar",
    "vocabulary": "vocabulary",
    "word_choice": "vocabulary",
    "collocation": "vocabulary",
    "pronunciation": "pronunciation",
    "politeness": "grammar",
    "expression": "vocabulary",
    "style": "vocabulary",
    "spelling": "vocabulary",
}


class ProgressService:
    """学习进度计算与统计。"""

    @staticmethod
    async def load_records(db: AsyncSession, user_id: str) -> list[dict]:
        """从数据库读取该用户的全部已结束会话记录。"""
        result = await db.execute(
            select(PracticeSessionRecord)
            .where(PracticeSessionRecord.user_id == user_id)
            .order_by(PracticeSessionRecord.ended_at)
        )
        records = []
        for row in result.scalars():
            try:
                rounds = json.loads(row.rounds_json or "[]")
            except json.JSONDecodeError:
                rounds = []
            records.append({
                "session_id": row.session_id,
                "mode": row.mode,
                "scenario": row.scenario,
                "user_level": row.user_level,
                "started_at": row.started_at,
                "ended_at": row.ended_at,
                "rounds": rounds,
            })
        return records

    @staticmethod
    def calculate_progress(user_id: str, sessions: list[dict]) -> dict[str, Any]:
        """从会话记录计算学习进度（T-006）。"""
        total_rounds = 0
        total_corrections = 0
        error_patterns = {"grammar": 0, "vocabulary": 0, "pronunciation": 0}
        error_examples: list[dict] = []
        daily_map: dict[str, dict] = {}

        for session in sessions:
            rounds = session.get("rounds", [])
            total_rounds += len(rounds)
            for r in rounds:
                correction = r.get("correction")
                if correction:
                    total_corrections += 1
                    raw_type = correction.get("type", "grammar")
                    etype = _ERROR_NORMALIZE.get(raw_type, "grammar")
                    error_patterns[etype] += 1
                    if len(error_examples) < 10:
                        error_examples.append({
                            "type": etype,
                            "original": correction.get("original", ""),
                            "corrected": correction.get("corrected", ""),
                        })

            # 每日活跃
            ended = session.get("ended_at")
            if ended:
                day = ended.strftime("%Y-%m-%d")
                entry = daily_map.setdefault(
                    day,
                    {"date": day, "sessions": 0, "rounds": 0, "corrections": 0},
                )
                entry["sessions"] += 1
                entry["rounds"] += len(rounds)
                entry["corrections"] += sum(
                    1 for r in rounds if r.get("correction")
                )

        # 薄弱环节：错误次数 > 2 且为占比最高的类型
        total_errors = sum(error_patterns.values())
        weaknesses: list[str] = []
        if total_errors > 0:
            sorted_types = sorted(
                error_patterns.items(), key=lambda kv: kv[1], reverse=True
            )
            top_count = sorted_types[0][1]
            for etype, count in sorted_types:
                if count > 2 or (total_errors >= 3 and count == top_count and count >= 2):
                    weaknesses.append(_ERROR_LABELS.get(etype, etype))

        # 强项：错误最少的维度（无错误时默认阅读）
        strengths: list[str] = []
        if total_errors > 0:
            min_type = min(error_patterns, key=lambda k: error_patterns[k])
            if error_patterns[min_type] == 0:
                strengths.append(_ERROR_LABELS.get(min_type, min_type))
        else:
            strengths = ["暂无高频错误记录"]

        # 每日日志（按日期升序）
        daily_logs = sorted(daily_map.values(), key=lambda d: d["date"])

        # 近 7 天 / 30 天活跃度
        now = datetime.now(timezone.utc).date()
        active_7 = sum(
            1 for d in daily_logs
            if datetime.strptime(d["date"], "%Y-%m-%d").date() >= now - timedelta(days=7)
        )
        active_30 = sum(
            1 for d in daily_logs
            if datetime.strptime(d["date"], "%Y-%m-%d").date() >= now - timedelta(days=30)
        )

        return {
            "userId": user_id,
            "totalDays": len(daily_logs),
            "totalSessions": len(sessions),
            "totalRounds": total_rounds,
            "totalCorrections": total_corrections,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "errorPatterns": error_patterns,
            "errorExamples": error_examples[:5],
            "dailyLogs": daily_logs,
            "activeDays7": active_7,
            "activeDays30": active_30,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
