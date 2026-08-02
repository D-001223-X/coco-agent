"""智能反馈生成服务（T-006）。

基于学习进度数据，调用 DeepSeek 生成个性化学习建议。
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

FEEDBACK_PROMPT = """\
你是一位专业的学习分析师。基于以下学习数据，生成个性化反馈报告。

## 学习数据
- 用户等级：{level}
- 会话次数：{sessions}
- 总对话轮次：{rounds}
- 总纠错次数：{corrections}
- 主要错误类型：{error_types}
- 薄弱环节：{weaknesses}

## 报告要求
1. 肯定用户的学习努力（1句话）
2. 指出主要进步（1句话）
3. 指出薄弱环节（1句话）
4. 给出下一步建议（2-3条具体可执行建议）

## 输出格式
直接输出文本，不超过200字。
"""


class FeedbackService:
    """根据进度数据生成个性化反馈。"""

    def __init__(self) -> None:
        self._settings = get_settings()

    async def generate_feedback(
        self, progress_data: dict[str, Any], user_level: str
    ) -> str:
        """生成智能反馈报告。

        Returns
        -------
        str
            反馈文本；无 API key 或失败时返回兜底建议。
        """
        error_patterns = progress_data.get("errorPatterns", {})
        top_errors = sorted(
            error_patterns.items(), key=lambda kv: kv[1], reverse=True
        )
        error_summary = ", ".join(
            f"{k}: {v}次" for k, v in top_errors[:3] if v > 0
        ) or "暂无"
        weaknesses = "、".join(progress_data.get("weaknesses", [])) or "暂无"

        prompt = FEEDBACK_PROMPT.format(
            level=user_level,
            sessions=progress_data.get("totalSessions", 0),
            rounds=progress_data.get("totalRounds", 0),
            corrections=progress_data.get("totalCorrections", 0),
            error_types=error_summary,
            weaknesses=weaknesses,
        )

        # Mock 模式：无 API key 返回规则化建议
        if not self._settings.dashscope_api_key:
            return self._fallback_feedback(progress_data, user_level)

        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._settings.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._settings.dashscope_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._settings.deepseek_model,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": "请生成我的学习反馈报告"},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 512,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0]["message"]["content"].strip()
            return self._fallback_feedback(progress_data, user_level)
        except Exception as exc:
            logger.warning("反馈生成失败，使用兜底: %s", exc)
            return self._fallback_feedback(progress_data, user_level)

    @staticmethod
    def _fallback_feedback(progress_data: dict[str, Any], user_level: str) -> str:
        """无 API key / 失败时的规则化兜底建议。"""
        weaknesses = progress_data.get("weaknesses", []) or ["语法"]
        return (
            f"很棒，你已经完成了 {progress_data.get('totalSessions', 0)} 次陪练、"
            f"{progress_data.get('totalRounds', 0)} 轮对话！"
            f"下一步建议：1）每天坚持 15 分钟口语练习；"
            f"2）重点突破薄弱环节（{'、'.join(weaknesses)}）；"
            f"3）多使用完整句式表达观点。继续加油！"
        )
