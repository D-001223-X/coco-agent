"""Pydantic schemas for bad-case (data flywheel) admin APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BadCaseOut(BaseModel):
    id: int
    trace_id: str | None = None
    user_question: str
    system_answer: str | None = None
    intent: str | None = None
    source: str
    status: str
    ideal_answer: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    calibrated_by: str | None = None
    stored_at: datetime | None = None


class BadCaseUpdateIn(BaseModel):
    status: str | None = None  # calibrated / ignored / pending
    ideal_answer: str | None = None


class BadCaseGenerateOut(BaseModel):
    draft: str


class BadCaseStoreOut(BaseModel):
    ok: bool
    message: str
    bad_case_id: int
