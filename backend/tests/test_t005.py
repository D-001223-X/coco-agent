"""T-005: Rerank service tests.

Covers 3 scenarios:
  1. Normal: mock returns reversed order → service corrects it
  2. Boundary: empty documents → empty list, no API call
  3. Exception: API timeout → returns originals, no crash
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.rerank_service import RerankService


# ── Fixtures ──────────────────────────────────────────────
@pytest.fixture
def service():
    return RerankService()


# ── Helper: build a mock httpx response ───────────────────
def _mock_rerank_response(
    items: list[dict],
) -> MagicMock:
    """Build a fake httpx.Response with the given results items."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.json.return_value = {"results": items}
    return mock_resp


# ── Test 1: Normal — API returns reversed order, service fixes ──
async def test_rerank_normal(service):
    """Service should sort documents by relevance_score descending."""
    docs = [
        "可可语伴会员每月68元",
        "可可语伴免费版每天20分钟",
    ]
    mock_resp = _mock_rerank_response([
        {"index": 1, "relevance_score": 0.9},
        {"index": 0, "relevance_score": 0.8},
    ])

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await service.rerank("会员多少钱？", docs, top_k=2)

    assert len(result) == 2
    # Index 1 (会员每月68元) should be first because it has higher score
    assert result[0] == (docs[1], 0.9), f"Expected (doc[1], 0.9) first, got {result[0]}"
    assert result[1] == (docs[0], 0.8), f"Expected (doc[0], 0.8) second, got {result[1]}"
    assert result[0][1] > result[1][1], "Scores should be descending"


# ── Test 2: Boundary — empty documents ──────────────────────
async def test_rerank_empty_documents(service):
    """Empty documents should return empty list without calling API."""
    with patch("httpx.AsyncClient.post") as mock_post:
        result = await service.rerank("会员多少钱？", [], top_k=3)

    assert result == []
    mock_post.assert_not_called()


# ── Test 3: Exception — API timeout → degrade to originals ──
async def test_rerank_api_timeout_degrade(service):
    """API timeout should return original documents with score 0.0, no crash."""
    docs = [
        "可可语伴会员每月68元",
        "可可语伴免费版每天20分钟",
        "可可语伴家庭计划每月168元",
    ]

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=TimeoutError("Connection timed out"),
    ):
        result = await service.rerank("会员多少钱？", docs, top_k=2)

    assert len(result) == 2  # truncated to top_k
    assert result == [(docs[0], 0.0), (docs[1], 0.0)]
    assert all(score == 0.0 for _, score in result)
