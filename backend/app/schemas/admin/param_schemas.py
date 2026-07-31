"""Pydantic schemas for retrieval-parameter admin APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParamsOut(BaseModel):
    faiss_top_k: int = Field(ge=5, le=100)
    fts5_top_k: int = Field(ge=5, le=100)
    threshold: float = Field(ge=0.0, le=1.0)
    rrf_k: int = Field(ge=10, le=200)
    final_top_k: int = Field(ge=1, le=10)


class ParamsUpdateIn(BaseModel):
    faiss_top_k: int | None = Field(default=None, ge=5, le=100)
    fts5_top_k: int | None = Field(default=None, ge=5, le=100)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    rrf_k: int | None = Field(default=None, ge=10, le=200)
    final_top_k: int | None = Field(default=None, ge=1, le=10)
