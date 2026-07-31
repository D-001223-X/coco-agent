"""Pydantic schemas for prompt admin APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PromptOut(BaseModel):
    name: str
    content: str
    version: int


class PromptUpdateIn(BaseModel):
    content: str
    make_permanent: bool = False


class PromptHistoryOut(BaseModel):
    id: int
    version: int
    content: str
    is_permanent: bool
    created_at: datetime | None = None
    created_by: str | None = None


class PromptTestIn(BaseModel):
    content: str | None = None
    question: str = "会员多少钱？"


class PromptTestOut(BaseModel):
    intent: str
    resolved_question: str
    response: str
    useful: bool
