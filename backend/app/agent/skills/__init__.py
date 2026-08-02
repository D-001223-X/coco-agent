"""Skill 调度系统（T-004/T-005）。

根据 mode 加载对应 Skill 实例；场景/话题从配置文件读取。
"""

from __future__ import annotations

from app.agent.skills.base import BaseSkill
from app.agent.skills.configs.discussion_topics import DISCUSSION_TOPICS
from app.agent.skills.configs.freechat_topics import FREECHAT_TOPICS
from app.agent.skills.configs.roleplay_scenarios import ROLEPLAY_SCENARIOS
from app.agent.skills.freechat import FreeChatSkill
from app.agent.skills.roleplay import RolePlaySkill
from app.agent.skills.topic import TopicSkill

SKILL_REGISTRY: dict[str, type[BaseSkill]] = {
    "roleplay": RolePlaySkill,
    "freechat": FreeChatSkill,
    "topic": TopicSkill,
}


def _scenario_list(cfg: dict) -> list[dict]:
    """把配置 dict 转为前端可用的场景列表。"""
    return [
        {
            "id": v["id"],
            "name": v["name"],
            "icon": v["icon"],
            "description": v["description"],
            "difficulty": v.get("difficulty", "medium"),
            "tags": v.get("tags", []),
            "role": v.get("role"),
            "category": v.get("category"),
            "guidingQuestions": v.get("guiding_questions", []),
            "expansionQuestions": v.get("expansion_questions", []),
        }
        for v in cfg.values()
    ]


_MODE_META = {
    "roleplay": {
        "id": "roleplay",
        "label": "角色扮演",
        "icon": "🎭",
        "description": "在真实场景中练习对话",
        "scenarios": _scenario_list(ROLEPLAY_SCENARIOS),
    },
    "freechat": {
        "id": "freechat",
        "label": "自由对话",
        "icon": "💬",
        "description": "自选话题，自然交流",
        "scenarios": _scenario_list(FREECHAT_TOPICS),
    },
    "topic": {
        "id": "topic",
        "label": "话题讨论",
        "icon": "📝",
        "description": "深度讨论，拓展表达",
        "scenarios": _scenario_list(DISCUSSION_TOPICS),
    },
}


def load_skill(mode: str, user_level: str, scenario: str = "") -> BaseSkill:
    """根据模式加载对应的 Skill 实例。"""
    skill_class = SKILL_REGISTRY.get(mode)
    if not skill_class:
        raise ValueError(f"未知的陪练模式: {mode}")
    # 场景配置是 dict（含 id/name），Skill 内按 id 或 name 匹配
    return skill_class(user_level, scenario)


def get_available_modes() -> list[dict]:
    """返回所有可用模式及场景列表（含难度/标签等元数据）。"""
    return list(_MODE_META.values())


def get_default_scenario(mode: str) -> str:
    """返回某模式的默认场景 id。"""
    meta = _MODE_META.get(mode)
    if not meta or not meta["scenarios"]:
        return ""
    return meta["scenarios"][0]["id"]


__all__ = [
    "BaseSkill",
    "DISCUSSION_TOPICS",
    "FREECHAT_TOPICS",
    "ROLEPLAY_SCENARIOS",
    "SKILL_REGISTRY",
    "get_available_modes",
    "get_default_scenario",
    "load_skill",
]
