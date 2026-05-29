"""测试 AI Handler 层。"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from insightor.ai.types import AIResponse, TokenUsage
from insightor.ai.litellm_handler import LiteLLMHandler
from insightor.ai.cached_handler import CachedAIHandler


# =============================================================================
# TokenUsage / AIResponse
# =============================================================================

class TestTokenUsage:
    def test_defaults(self):
        u = TokenUsage()
        assert u.total_tokens == 0

    def test_basic(self):
        u = TokenUsage(prompt_tokens=100, completion_tokens=50)
        assert u.total_tokens == 0  # not auto-summed
        assert u.prompt_tokens == 100


class TestAIResponse:
    def test_defaults(self):
        r = AIResponse()
        assert r.content == ""
        assert r.finish_reason == ""

    def test_full(self):
        r = AIResponse(content="hello", model="gpt-4o", finish_reason="stop",
                       usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                       duration_ms=2000)
        assert r.content == "hello"
        assert r.usage.total_tokens == 15
        assert r.duration_ms == 2000


# =============================================================================
# LiteLLMHandler
# =============================================================================

class TestLiteLLMHandler:
    def test_resolve_model_openai(self):
        assert LiteLLMHandler._resolve_model("gpt-4o") == "openai/gpt-4o"
        assert LiteLLMHandler._resolve_model("o3-mini") == "openai/o3-mini"

    def test_resolve_model_deepseek(self):
        assert LiteLLMHandler._resolve_model("deepseek-v3") == "deepseek/deepseek-v3"

    def test_resolve_model_claude(self):
        assert "anthropic/" in LiteLLMHandler._resolve_model("claude-sonnet-4-6")

    def test_resolve_already_prefixed(self):
        assert LiteLLMHandler._resolve_model("openai/gpt-4o") == "openai/gpt-4o"

    def test_build_messages(self):
        msgs = LiteLLMHandler._build_messages("sys", "usr")
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_build_messages_no_system(self):
        msgs = LiteLLMHandler._build_messages("", "usr")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chat_completion_basic(self):
        handler = LiteLLMHandler()
        mock_resp = {
            "content": "hello",
            "model": "openai/gpt-4o",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
        }
        with patch.object(handler, '_call_with_retry', AsyncMock(return_value=mock_resp)):
            resp = await handler.chat_completion("gpt-4o", "sys", "usr")
            assert resp.content == "hello"
            assert resp.finish_reason == "stop"
            assert resp.usage.total_tokens == 6
            assert resp.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_fallback_on_error(self):
        handler = LiteLLMHandler(fallback_models=["deepseek-v3"])
        with patch.object(handler, '_call_with_retry', AsyncMock(side_effect=RuntimeError("fail"))):
            with patch.object(handler, '_try_fallback', AsyncMock(return_value=AIResponse(
                content="fallback", model="deepseek/deepseek-v3", finish_reason="stop"
            ))):
                resp = await handler.chat_completion("gpt-4o", "sys", "usr")
                assert resp.content == "fallback"


# =============================================================================
# CachedAIHandler
# =============================================================================

class TestCachedAIHandler:
    @pytest.fixture
    def mock_handler(self):
        h = MagicMock()
        h.chat_completion = AsyncMock(return_value=AIResponse(
            content="fresh", model="test", finish_reason="stop",
        ))
        return h

    @pytest.mark.asyncio
    async def test_first_call_miss(self, mock_handler, tmp_path):
        cached = CachedAIHandler(mock_handler, cache_dir=str(tmp_path))
        resp = await cached.chat_completion("test-model", "sys", "user1")
        assert resp.content == "fresh"
        mock_handler.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_call_hit(self, mock_handler, tmp_path):
        cached = CachedAIHandler(mock_handler, cache_dir=str(tmp_path))
        resp1 = await cached.chat_completion("test-model", "sys", "user2")
        resp2 = await cached.chat_completion("test-model", "sys", "user2")
        assert resp1.content == "fresh"
        assert resp2.content == "fresh"
        assert resp2.duration_ms == 0  # cache hit
        mock_handler.chat_completion.assert_called_once()  # 只调用了一次

    @pytest.mark.asyncio
    async def test_different_prompt_miss(self, mock_handler, tmp_path):
        cached = CachedAIHandler(mock_handler, cache_dir=str(tmp_path))
        await cached.chat_completion("m", "sys", "a")
        await cached.chat_completion("m", "sys", "b")
        assert mock_handler.chat_completion.call_count == 2  # 两次不同 prompt
