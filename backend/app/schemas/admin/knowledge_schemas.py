"""Pydantic schemas for knowledge-base admin APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class KnowledgeFileOut(BaseModel):
    filename: str
    size: int
    modified_at: datetime | None = None


class KnowledgeListOut(BaseModel):
    files: list[KnowledgeFileOut]


class KnowledgeStatusOut(BaseModel):
    chunk_count: int
    last_build_at: datetime | None = None
    index_path: str
