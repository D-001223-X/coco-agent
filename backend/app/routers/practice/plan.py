"""Practice plan generation router (T-003).

POST /api/practice/plan/generate — uses DeepSeek to build a personalized
learning plan from the assessment result + user goals.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import get_settings
from app.models import User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/practice/plan", tags=["practice-plan"])

UserDep = Annotated[User, Depends(get_current_user)]

# 计划生成 System Prompt（CEFR 规则来自知识库）
# MARKER: PLAN_PROMPT_START
_PLAN_SYSTEM_PROMPT = """\
你是可可语伴的AI学习规划师。根据用户的测评结果和学习目标，生成一份个性化的英语学习计划。

测评结果：{assessment}
学习目标：{goals}

CEFR 等级参考：
- A1 入门级：能理解和使用非常基础的短语和表达
- A2 基础级：能理解最直接相关领域的句子和表达
- B1 进阶级：能理解工作、学习、休闲等熟悉领域的标准输入
- B2 中高级：能理解具体和抽象主题的复杂文本

你必须且只能输出一个合法的 JSON 对象，不要输出任何其他内容（不要 markdown 代码块标记）。JSON 结构如下：
{{
  "overview": "整体路径概述（≤200字，从当前等级到目标等级的计划摘要）",
  "milestones": [
    {{"title": "里程碑标题", "description": "具体内容描述", "weeks": 2}}
  ],
  "recommendedScenarios": ["推荐场景1", "推荐场景2"]
}}

要求：
1. milestones 输出 3-5 个，按时间顺序排列
2. 里程碑必须基于用户的当前 CEFR 等级和薄弱维度
3. 场景要与用户的备考/学习目标匹配
4. weeks 为完成该里程碑的周数（正整数）
"""
# MARKER: PLAN_PROMPT_END


class AssessmentIn(BaseModel):
    cefrLevel: str
    listeningScore: int = 0
    speakingScore: int = 0
    readingScore: int = 0


class GoalsIn(BaseModel):
    goal: str
    targetLevel: str
    dailyTime: int = 30
    style: list[str] = []
    examDate: str | None = None


class PlanGenerateIn(BaseModel):
    userId: str = "user_001"
    assessment: AssessmentIn
    goals: GoalsIn


@router.post("/generate")
async def generate_plan(body: PlanGenerateIn, _user: UserDep):
    """根据测评结果 + 用户目标生成学习计划（DeepSeek）。"""
    s = get_settings()
    if not s.dashscope_api_key:
        # Mock 模式：返回结构化默认计划
        return {
            "code": 0,
            "data": _mock_plan(body),
            "msg": "success",
            "mock": True,
        }

    prompt = _PLAN_SYSTEM_PROMPT.format(
        assessment=json.dumps(body.assessment.model_dump(), ensure_ascii=False),
        goals=json.dumps(body.goals.model_dump(), ensure_ascii=False),
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{s.deepseek_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {s.dashscope_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": s.deepseek_model,
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "请为我生成学习计划"},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices", [])
        if not choices:
            raise ValueError("DeepSeek returned no choices")
        raw = choices[0]["message"]["content"].strip()

        # 解析 JSON（兼容 markdown 代码块包裹）
        parsed = _parse_json_response(raw)

        plan = {
            "planId": f"plan_{uuid.uuid4().hex[:8]}",
            "userId": body.userId,
            "overview": parsed.get("overview", "已生成学习计划"),
            "milestones": [
                {
                    "id": f"m{i+1}",
                    "title": m.get("title", f"里程碑{i+1}"),
                    "description": m.get("description", ""),
                    "weeks": int(m.get("weeks", 2)),
                    "completed": False,
                }
                for i, m in enumerate(parsed.get("milestones", [])[:5])
            ],
            "recommendedScenarios": parsed.get("recommendedScenarios", []),
            "status": "进行中",
            "generatedAt": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
        }
        if not plan["milestones"]:
            raise ValueError("LLM 未返回有效里程碑")
        return {"code": 0, "data": plan, "msg": "success"}

    except Exception as exc:
        logger.error("plan generate failed: %s", exc)
        return {
            "code": 500,
            "data": None,
            "msg": f"计划生成失败: {exc}",
        }


def _parse_json_response(raw: str) -> dict[str, Any]:
    """解析 LLM JSON 输出，兼容代码块包裹。"""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    raise ValueError(f"无法解析 LLM 计划输出: {raw[:200]}")


def _mock_plan(body: PlanGenerateIn) -> dict[str, Any]:
    """Mock 模式（无 API key）返回的默认计划。"""
    return {
        "planId": f"plan_{uuid.uuid4().hex[:8]}",
        "userId": body.userId,
        "overview": (
            f"从 {body.assessment.cefrLevel} 到 {body.goals.targetLevel} 的个性化计划，"
            f"目标：{body.goals.goal}，每日投入 {body.goals.dailyTime} 分钟。"
        ),
        "milestones": [
            {
                "id": "m1",
                "title": "基础巩固",
                "description": "强化当前等级的核心词汇与语法",
                "weeks": 2,
                "completed": False,
            },
            {
                "id": "m2",
                "title": "能力提升",
                "description": "围绕目标场景进行专项训练",
                "weeks": 3,
                "completed": False,
            },
            {
                "id": "m3",
                "title": "冲刺达标",
                "description": "模拟演练与查漏补缺",
                "weeks": 2,
                "completed": False,
            },
        ],
        "recommendedScenarios": ["餐厅点餐", "旅行问路", "面试对话"],
        "status": "进行中",
        "generatedAt": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }
