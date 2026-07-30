"""Tests for app.config.Settings validation and dynamic URL properties."""

import os

import pytest


# ──────────────────────────────────────────────────────────────
# Normal: config reads valid env vars and returns correct values
# ──────────────────────────────────────────────────────────────
def test_config_reads_valid_env(monkeypatch):
    """With DASHSCOPE_API_KEY and WORKSPACE_ID set, Settings loads fine."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-test-12345")
    monkeypatch.setenv("WORKSPACE_ID", "ws-abc-def")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")

    from app.config import Settings

    s = Settings()
    assert s.dashscope_api_key == "sk-test-12345"
    assert s.workspace_id == "ws-abc-def"
    assert s.database_url == "sqlite+aiosqlite:///./test.db"
    assert s.algorithm == "HS256"
    assert s.top_k == 5
    assert s.score_threshold == 0.15  # matches current .env


# ──────────────────────────────────────────────────────────────
# Dynamic URL properties
# ──────────────────────────────────────────────────────────────
def test_config_dynamic_urls(monkeypatch):
    """The 3 @property URLs should assemble correctly."""
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-x")
    monkeypatch.setenv("WORKSPACE_ID", "my-ws-001")

    from app.config import Settings

    s = Settings()
    assert (
        s.deepseek_base_url
        == "https://my-ws-001.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )
    assert (
        s.embedding_base_url
        == "https://my-ws-001.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )
    assert (
        s.rerank_base_url
        == "https://my-ws-001.cn-beijing.maas.aliyuncs.com/compatible-api/v1"
    )


# ──────────────────────────────────────────────────────────────
# Exception: missing DASHSCOPE_API_KEY
# ──────────────────────────────────────────────────────────────
def test_config_missing_dashscope_api_key(monkeypatch, tmp_path):
    """Missing DASHSCOPE_API_KEY should raise ValueError."""
    # Change to a temp directory without .env so pydantic-settings
    # falls back to os.environ
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.setenv("WORKSPACE_ID", "ws-ok")

    from app.config import Settings

    with pytest.raises(ValueError, match="DASHSCOPE_API_KEY"):
        Settings()


# ──────────────────────────────────────────────────────────────
# Exception: missing WORKSPACE_ID
# ──────────────────────────────────────────────────────────────
def test_config_missing_workspace_id(monkeypatch, tmp_path):
    """Missing WORKSPACE_ID should raise ValueError."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-ok")
    monkeypatch.delenv("WORKSPACE_ID", raising=False)

    from app.config import Settings

    with pytest.raises(ValueError, match="WORKSPACE_ID"):
        Settings()


# ──────────────────────────────────────────────────────────────
# Exception: both missing
# ──────────────────────────────────────────────────────────────
def test_config_missing_both(monkeypatch, tmp_path):
    """Missing both required vars should mention both names."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("WORKSPACE_ID", raising=False)

    from app.config import Settings

    with pytest.raises(ValueError) as exc_info:
        Settings()

    msg = str(exc_info.value)
    assert "DASHSCOPE_API_KEY" in msg
    assert "WORKSPACE_ID" in msg
