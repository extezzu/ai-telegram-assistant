"""Tests for the OpenAI API client wrapper."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from bot.ai_client import AIClient, AIClientError, AIResponse
from bot.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        telegram_bot_token="test-token",
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        openai_max_tokens=100,
        openai_temperature=0.7,
        redis_url="redis://localhost:6379/0",
        max_conversation_length=10,
        rate_limit_per_minute=5,
        default_system_prompt="Test prompt.",
        health_check_port=8080,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_openai_response() -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello! How can I help you?"
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 8
    response.usage.total_tokens = 18
    return response


class TestAIClient:

    @pytest.mark.asyncio
    async def test_generate_success(self, settings, mock_openai_response):
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )

        result = await client.generate(
            [{"role": "user", "content": "Hello"}]
        )

        assert isinstance(result, AIResponse)
        assert result.content == "Hello! How can I help you?"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 8
        assert result.total_tokens == 18

    @pytest.mark.asyncio
    async def test_generate_none_content(self, settings):
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        response.usage.prompt_tokens = 5
        response.usage.completion_tokens = 0
        response.usage.total_tokens = 5

        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            return_value=response
        )

        result = await client.generate(
            [{"role": "user", "content": "Hi"}]
        )
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_connection_error(self, settings):
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(AIClientError, match="Could not connect"):
            await client.generate(
                [{"role": "user", "content": "Hi"}]
            )

    @pytest.mark.asyncio
    async def test_timeout_error(self, settings):
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        with pytest.raises(AIClientError, match="timed out"):
            await client.generate(
                [{"role": "user", "content": "Hi"}]
            )

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, settings):
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            )
        )

        with pytest.raises(AIClientError, match="busy"):
            await client.generate(
                [{"role": "user", "content": "Hi"}]
            )

    @pytest.mark.asyncio
    async def test_unexpected_error(self, settings):
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("Something broke")
        )

        with pytest.raises(AIClientError, match="unexpected"):
            await client.generate(
                [{"role": "user", "content": "Hi"}]
            )

    @pytest.mark.asyncio
    async def test_close(self, settings):
        client = AIClient(settings)
        client._client = AsyncMock()

        await client.close()
        client._client.close.assert_awaited_once()
