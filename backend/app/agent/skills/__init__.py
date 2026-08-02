"""Skill 调度系统（T-004）。

根据 mode 加载对应 Skill 实例。
"""

from __future__ import annotations

from app.agent.skills.base import BaseSkill
from app.agent.skills.freechat import FreeChatSkill
from app.agent.skills.roleplay import RolePlaySkill
from app.agent.skills.topic import TopicSkill

SKILL_REGISTRY: dict[str, type[BaseSkill]] = {
    "roleplay": RolePlaySkill,
    "freechat": FreeChatSkill,
    "topic": TopicSkill,
}

_MODE_META = {
    "roleplay": {
        "id": "roleplay",
        "label": "角色扮演",
        "icon": "🎭",
        "description": "在真实场景中练习对话",
        "scenarios": list(RolePlaySkill.SCENARIOS.keys()),
    },
    "freechat": {
        "id": "freechat",
        "label": "自由对话",
        "icon": "💬",
        "description": "自选话题，自然交流",
        "scenarios": list(FreeChatSkill.TOPICS),
    },
    "topic": {
        "id": "topic",
        "label": "话题讨论",
        "icon": "📝",
        "description": "深度讨论，拓展表达",
        "scenarios": list(TopicSkill.DISCUSSIONS.keys()),
    },
}


def load_skill(mode: str, user_level: str, scenario: str = "") -> BaseSkill:
    """根据模式加载对应的 Skill 实例。"""
    skill_class = SKILL_REGISTRY.get(mode)
    if not skill_class:
        raise ValueError(f"未知的陪练模式: {mode}")
    return skill_class(user_level, scenario)


def get_available_modes() -> list[dict]:
    """返回所有可用模式及场景列表。"""
    return list(_MODE_META.values())


def get_default_scenario(mode: str) -> str:
    """返回某模式的默认场景。"""
    meta = _MODE_META.get(mode)
    if not meta:
        return ""
    return meta["scenarios"][0] if meta["scenarios"] else ""


__all__ = [
    "BaseSkill",
    "SKILL_REGISTRY",
    "get_available_modes",
    "get_default_scenario",
    "load_skill",
]
