"""Tests for the OpenAI API client wrapper."""

from unittest.mock import AsyncMock, MagicMock

import pytest

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
    """Create a mock OpenAI chat completion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = "Hello! How can I help you?"
    response.usage.prompt_tokens = 10
    response.usage.completion_tokens = 8
    response.usage.total_tokens = 18
    return response


class TestAIClient:
    """Test AIClient wrapper."""

    @pytest.mark.asyncio
    async def test_generate_success(self, settings: Settings, mock_openai_response: MagicMock) -> None:
        """Should return AIResponse on successful generation."""
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(return_value=mock_openai_response)

        messages = [{"role": "user", "content": "Hello"}]
        result = await client.generate(messages)

        assert isinstance(result, AIResponse)
        assert result.content == "Hello! How can I help you?"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 8
        assert result.total_tokens == 18

    @pytest.mark.asyncio
    async def test_generate_empty_content(self, settings: Settings) -> None:
        """Should handle None content gracefully."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        response.usage.prompt_tokens = 5
        response.usage.completion_tokens = 0
        response.usage.total_tokens = 5

        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(return_value=response)

        result = await client.generate([{"role": "user", "content": "Hi"}])
        assert result.content == ""

    @pytest.mark.asyncio
    async def test_generate_connection_error(self, settings: Settings) -> None:
        """Should raise AIClientError on connection failure."""
        from openai import APIConnectionError

        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(AIClientError, match="Could not connect"):
            await client.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_timeout_error(self, settings: Settings) -> None:
        """Should raise AIClientError on timeout."""
        from openai import APITimeoutError

        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        with pytest.raises(AIClientError, match="timed out"):
            await client.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_rate_limit_error(self, settings: Settings) -> None:
        """Should raise AIClientError on rate limit."""
        from openai import RateLimitError

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
            await client.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_generate_unexpected_error(self, settings: Settings) -> None:
        """Should raise AIClientError on unexpected errors."""
        client = AIClient(settings)
        client._client = AsyncMock()
        client._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("Something broke")
        )

        with pytest.raises(AIClientError, match="unexpected"):
            await client.generate([{"role": "user", "content": "Hi"}])

    @pytest.mark.asyncio
    async def test_close(self, settings: Settings) -> None:
        """Should close the underlying client."""
        client = AIClient(settings)
        client._client = AsyncMock()

        await client.close()
        client._client.close.assert_awaited_once()
