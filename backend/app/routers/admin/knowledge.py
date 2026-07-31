"""Knowledge-base admin router (P0): list/upload/delete/rebuild/status."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.models import User
from app.routers.admin.deps import verify_admin
from app.services.admin.knowledge_service import KnowledgeService

router = APIRouter(prefix="/api/admin/knowledge", tags=["admin-knowledge"])

_service = KnowledgeService()


@router.get("/list")
async def list_knowledge_files(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """List all .md files under knowledge_base/."""
    try:
        files = _service.list_files()
        return {"code": 0, "data": {"files": files}, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/upload")
async def upload_knowledge_file(
    _admin: Annotated[User, Depends(verify_admin)],
    file: UploadFile = File(...),
):
    """Upload a .md file to knowledge_base/."""
    try:
        content = await file.read()
        result = await _service.upload_file(file.filename or "upload.md", content)
        return {"code": 0, "data": result, "msg": "success"}
    except ValueError as exc:
        return {"code": 400, "data": None, "msg": str(exc)}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.delete("/{filename}")
async def delete_knowledge_file(
    filename: str,
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Delete a knowledge file (admin-confirmed operation)."""
    try:
        result = await _service.delete_file(filename)
        return {"code": 0, "data": result, "msg": "success"}
    except FileNotFoundError as exc:
        return {"code": 404, "data": None, "msg": str(exc)}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}


@router.post("/rebuild")
async def rebuild_knowledge_index(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Rebuild FAISS/FTS5 index from knowledge base (blocking)."""
    result = await _service.rebuild_index()
    code = 0 if result.get("ok") else 500
    return {"code": code, "data": result, "msg": result.get("message", "success")}


@router.get("/status")
async def knowledge_index_status(
    _admin: Annotated[User, Depends(verify_admin)],
):
    """Return index status: chunk count, last build time."""
    try:
        status = _service.get_status()
        return {"code": 0, "data": status, "msg": "success"}
    except Exception as exc:
        return {"code": 500, "data": None, "msg": str(exc)}
