"""Prompt admin router (P0): list/get/update/history/restore/test."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.database import get_db
from app.models import User
from app.routers.admin.deps import verify_admin
from app.schemas.admin.prompt_schemas import PromptTestIn, PromptUpdateIn
from app.services.admin.prompt_service import PROMPT_NAMES, prompt_service
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin/prompts", tags=["admin-prompts"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[User, Depends(verify_admin)]


@router.get("")
async def list_prompts(
    _admin: AdminDep,
):
    """List all three prompts (intent / support / chat)."""
    prompts = []
    for name in PROMPT_NAMES:
        try:
            p = prompt_service.get_prompt(name)
            prompts.append(p)
        except ValueError:
            continue
    return {"code": 0, "data": {"prompts": prompts}, "msg": "success"}


@router.get("/{name}")
async def get_prompt(
    name: str,
    _admin: AdminDep,
):
    """Get a single prompt's current content."""
    try:
        p = prompt_service.get_prompt(name)
        return {"code": 0, "data": p, "msg": "success"}
    except ValueError as exc:
        return {"code": 404, "data": None, "msg": str(exc)}


@router.put("/{name}")
async def update_prompt(
    name: str,
    body: PromptUpdateIn,
    _admin: AdminDep,
    db: DbDep,
):
    """Update a prompt (writes marker block back to source file)."""
    try:
        result = await prompt_service.update_prompt(
            name, body.content, body.make_permanent, _admin.email, db
        )
        return {"code": 0, "data": result, "msg": "success"}
    except ValueError as exc:
        return {"code": 404, "data": None, "msg": str(exc)}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.get("/{name}/history")
async def prompt_history(
    name: str,
    _admin: AdminDep,
    db: DbDep,
):
    """Return version history for a prompt (latest 20)."""
    try:
        history = await prompt_service.get_history(name, db, limit=20)
        return {"code": 0, "data": {"name": name, "history": history}, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/{name}/restore/{version}")
async def restore_prompt_version(
    name: str,
    version: int,
    _admin: AdminDep,
    db: DbDep,
):
    """Restore a prompt to a previous version (writes back to file)."""
    try:
        result = await prompt_service.restore_version(name, version, _admin.email, db)
        return {"code": 0, "data": result, "msg": "success"}
    except ValueError as exc:
        return {"code": 404, "data": None, "msg": str(exc)}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/{name}/test")
async def test_prompt(
    name: str,
    body: PromptTestIn,
    _admin: AdminDep,
):
    """Test a prompt against a sample question (uses live services)."""
    from app.services.intent_service import IntentService

    question = body.question
    try:
        if name == "intent":
            svc = IntentService()
            result = await svc.recognize(question, history=[])
            return {
                "code": 0,
                "data": {
                    "intent": result.intent,
                    "resolved_question": result.resolved_question,
                    "response": "",
                    "useful": True,
                },
                "msg": "success",
            }
        # support / chat / feedback → run through LLM service
        from app.services.llm_service import LLMService

        llm = LLMService()
        from app.services.retrieval_service import RetrievedChunk

        chunks: list[RetrievedChunk] = []
        intent = "SUPPORT"
        if name in ("support", "feedback"):
            from app.services.retrieval_service import RetrievalService

            retrieved = await RetrievalService().search(
                question, top_k=3, threshold=0.15
            )
            chunks = retrieved
            intent = "SUPPORT" if name == "support" else "FEEDBACK"
        else:  # chat
            intent = "CHAT"
        resp = await llm.generate(
            query=question,
            history=[],
            chunks=chunks,
            intent=intent,
        )
        return {
            "code": 0,
            "data": {
                "intent": intent,
                "resolved_question": question,
                "response": resp.get("content", ""),
                "useful": resp.get("useful", False),
            },
            "msg": "success",
        }
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}
