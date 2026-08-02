"""Prompt admin service: read/update prompts via file markers + version history.

Prompt storage locations:
  - intent          : backend/app/services/intent_service.py   (SYSTEM_PROMPT)
  - support         : backend/app/services/llm_service.py      (SUPPORT_SYSTEM_PROMPT)
  - chat            : backend/app/services/llm_service.py      (CHAT_SYSTEM_PROMPT)
  - feedback        : backend/app/services/prompts/feedback_prompt.py (FEEDBACK_SYSTEM_PROMPT)
  - plan            : backend/app/routers/practice/plan.py     (_PLAN_SYSTEM_PROMPT)
  - roleplay        : backend/app/agent/skills/roleplay.py     (ROLEPLAY_SYSTEM_PROMPT)
  - freechat        : backend/app/agent/skills/freechat.py     (FREECHAT_SYSTEM_PROMPT)
  - topic           : backend/app/agent/skills/topic.py        (TOPIC_SYSTEM_PROMPT)
  - feedback_report : backend/app/services/practice/feedback_service.py (FEEDBACK_PROMPT)
  - bad_case        : backend/app/services/admin/bad_case_service.py (DRAFT_PROMPT)

Each prompt is wrapped in ``# MARKER: <NAME>_PROMPT_START`` /
``# MARKER: <NAME>_PROMPT_END`` comment lines inside its source file.
Reading is dynamic (from disk on every call) so edits take effect immediately.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromptHistory

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent  # backend/

PROMPT_SOURCES: dict[str, Path] = {
    "intent": BACKEND_DIR / "app" / "services" / "intent_service.py",
    "support": BACKEND_DIR / "app" / "services" / "llm_service.py",
    "chat": BACKEND_DIR / "app" / "services" / "llm_service.py",
    "feedback": BACKEND_DIR / "app" / "services" / "prompts" / "feedback_prompt.py",
    # ── 新增 6 个（T-007 扩展）──
    "plan": BACKEND_DIR / "app" / "routers" / "practice" / "plan.py",
    "roleplay": BACKEND_DIR / "app" / "agent" / "skills" / "roleplay.py",
    "freechat": BACKEND_DIR / "app" / "agent" / "skills" / "freechat.py",
    "topic": BACKEND_DIR / "app" / "agent" / "skills" / "topic.py",
    "feedback_report": BACKEND_DIR / "app" / "services" / "practice" / "feedback_service.py",
    "bad_case": BACKEND_DIR / "app" / "services" / "admin" / "bad_case_service.py",
}

PROMPT_NAMES = [
    "intent", "support", "chat", "feedback",
    "plan", "roleplay", "freechat", "topic", "feedback_report", "bad_case",
]

_MARKER_RE = re.compile(
    r"# MARKER: (?P<name>\w+)_PROMPT_START\n"
    r"(?P<var>\w+)\s*=\s*\"\"\"\\?\n"
    r"(?P<body>.*?)"
    r"\"\"\"\n"
    r"# MARKER: \w+_PROMPT_END",
    re.DOTALL,
)


class PromptService:
    """File-based prompt management with DB version history."""

    # ── Read (dynamic, from disk) ────────────────────────────
    def get_prompt(self, name: str) -> dict:
        if name not in PROMPT_SOURCES:
            raise ValueError(f"未知提示词: {name}")
        path = PROMPT_SOURCES[name]
        content = self._extract_marker(path, name)
        if content is None:
            # Marker missing → fall back to whole-file heuristic (should not happen)
            raise ValueError(f"提示词 {name} 未找到 MARKER 标记")
        return {"name": name, "content": content, "version": 0}

    def _extract_marker(self, path: Path, name: str) -> str | None:
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        for m in _MARKER_RE.finditer(text):
            if m.group("name").upper() == name.upper():
                return m.group("body").strip("\n")
        return None

    # ── Update (write markers back to file) ─────────────────
    async def update_prompt(
        self, name: str, content: str, make_permanent: bool, user_email: str,
        db: AsyncSession,
    ) -> dict:
        if name not in PROMPT_SOURCES:
            raise ValueError(f"未知提示词: {name}")
        path = PROMPT_SOURCES[name]
        self._write_marker(path, name, content)

        # Record version history in DB
        version = await self._next_version(db, name)
        history = PromptHistory(
            prompt_name=name,
            content=content,
            version=version,
            is_permanent=make_permanent,
            created_by=user_email,
        )
        db.add(history)
        await db.commit()
        return {"name": name, "version": version}

    def _write_marker(self, path: Path, name: str, content: str) -> None:
        """Rewrite the marker block, preserving ``VAR = \"\"\"...\"\"\"`` structure."""
        text = path.read_text(encoding="utf-8")
        start = f"# MARKER: {name.upper()}_PROMPT_START"
        end = f"# MARKER: {name.upper()}_PROMPT_END"

        # Preserve the variable name used in the existing block
        var_name = "SYSTEM_PROMPT"
        for m in _MARKER_RE.finditer(text):
            if m.group("name").upper() == name.upper():
                var_name = m.group("var")
                break

        block = f'{start}\n{var_name} = """\\\n{content.strip()}\n"""\n{end}'

        has_marker = any(
            m.group("name").upper() == name.upper() for m in _MARKER_RE.finditer(text)
        )
        if has_marker:
            new_text = _MARKER_RE.sub(
                lambda m: block if m.group("name").upper() == name.upper() else m.group(0),
                text,
            )
        else:
            new_text = text + f"\n\n{block}\n"

        path.write_text(new_text, encoding="utf-8")
        logger.info("Prompt %s updated in %s", name, path.name)

    # ── Version history ─────────────────────────────────────
    async def _next_version(self, db: AsyncSession, name: str) -> int:
        result = await db.execute(
            select(PromptHistory.version)
            .where(PromptHistory.prompt_name == name)
            .order_by(PromptHistory.version.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        return (latest or 0) + 1

    async def get_history(self, name: str, db: AsyncSession, limit: int = 20) -> list[dict]:
        result = await db.execute(
            select(PromptHistory)
            .where(PromptHistory.prompt_name == name)
            .order_by(PromptHistory.id.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            {
                "id": r.id,
                "version": r.version,
                "content": r.content,
                "is_permanent": r.is_permanent,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "created_by": r.created_by,
            }
            for r in rows
        ]

    # ── Restore ─────────────────────────────────────────────
    async def restore_version(
        self, name: str, version: int, user_email: str, db: AsyncSession,
    ) -> dict:
        result = await db.execute(
            select(PromptHistory)
            .where(PromptHistory.prompt_name == name, PromptHistory.version == version)
            .order_by(PromptHistory.id.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"版本 {version} 不存在")
        self._write_marker(PROMPT_SOURCES[name], name, row.content)
        return {"name": name, "restored_version": version}


# Module-level singleton
prompt_service = PromptService()


def load_prompt(name: str) -> str:
    """Runtime helper used by intent/llm services to load the current prompt.

    Reads from disk on every call → admin edits take effect immediately.
    """
    return prompt_service.get_prompt(name)["content"]
