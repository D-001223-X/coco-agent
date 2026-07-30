"""T-006: LLM response generation service tests.

Covers 4 scenarios:
  1. SUPPORT + chunks → DeepSeek mock returns answer containing "68元/月"
  2. CHAT → friendly reply under 50 chars
  3. SUPPORT + empty chunks → refuse (useful=false), no API call
  4. API timeout → fallback "服务繁忙，请稍后再试"
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_service import INTENT_CHAT, INTENT_SUPPORT, LLMService
from app.services.retrieval_service import RetrievedChunk


# ── Fixtures ──────────────────────────────────────────────
@pytest.fixture
def service():
    return LLMService()


# ── Helper: build a mock httpx response ───────────────────
def _mock_deepseek_response(content: str) -> MagicMock:
    """Build a fake httpx.Response that looks like a DeepSeek chat response."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock(return_value=None)
    mock_resp.json.return_value = {
        "choices": [{"message": {"role": "assistant", "content": content}}]
    }
    return mock_resp


# ── Test data ─────────────────────────────────────────────
@pytest.fixture
def pricing_chunks():
    return [
        RetrievedChunk(
            chunk_id="4",
            content="会员订阅价格为每月68元，包含无限对话时长、无限收藏与复习、全部角色扮演场景、高级错误分析报告和导出学习记录功能。",
            score=0.85,
            section="五、账号与付费方案",
        ),
    ]


# ── Test 1: SUPPORT + chunks → knowledge answer ───────────
async def test_generate_support_with_chunks(service, pricing_chunks):
    """SUPPORT intent with chunks should return content based on knowledge."""
    mock_content = (
        "可可语伴会员每月68元。"
        "\nCocoMate membership costs 68 yuan per month."
    )
    mock_resp = _mock_deepseek_response(mock_content)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await service.generate(
            query="会员多少钱？",
            history=[],
            chunks=pricing_chunks,
            intent=INTENT_SUPPORT,
        )

    assert result["useful"] is True
    assert "68" in result["content"], f"Expected '68' in content, got: {result['content']}"


# ── Test 2: CHAT → friendly reply ≤50 chars ───────────────
async def test_generate_chat(service):
    """CHAT intent should return a friendly reply under 50 characters."""
    mock_resp = _mock_deepseek_response("你好呀！今天有什么想聊的吗？")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
        result = await service.generate(
            query="你好",
            history=[],
            chunks=[],
            intent=INTENT_CHAT,
        )

    assert result["useful"] is True
    assert len(result["content"]) <= 50, (
        f"CHAT reply too long: {len(result['content'])} chars"
    )
    assert result["translation"] == ""


# ── Test 3: SUPPORT + empty chunks → refuse, no API call ──
async def test_generate_support_no_chunks(service):
    """SUPPORT with empty chunks should return useful=false, never call DeepSeek."""
    with patch("httpx.AsyncClient.post") as mock_post:
        result = await service.generate(
            query="会员多少钱？",
            history=[],
            chunks=[],
            intent=INTENT_SUPPORT,
        )

    assert result["useful"] is False
    assert "暂时不能回答" in result["content"]
    mock_post.assert_not_called()


# ── Test 4: API timeout → fallback ─────────────────────────
async def test_generate_api_timeout(service, pricing_chunks):
    """API timeout should return fallback message, useful=false."""
    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=TimeoutError("Connection timed out"),
    ):
        result = await service.generate(
            query="会员多少钱？",
            history=[],
            chunks=pricing_chunks,
            intent=INTENT_SUPPORT,
        )

    assert result["useful"] is False
    assert "服务繁忙" in result["content"]
