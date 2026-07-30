"""pytest configuration: async mode, fixtures, shared helpers."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Ensure backend/ is on sys.path so ``app`` is importable
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# ── Default env vars so config.py doesn't blow up on import ──
os.environ.setdefault("DASHSCOPE_API_KEY", "test-key")
os.environ.setdefault("WORKSPACE_ID", "test-ws-id")

# Enable auto-asyncio with function scope (fast, isolated)
pytestmark = pytest.mark.asyncio


def pytest_collection_modifyitems(config, items):
    """Automatically mark all async tests with asyncio."""
    for item in items:
        if asyncio.iscoroutinefunction(item.obj):
            item.add_marker(pytest.mark.asyncio)
