"""Tests for rate limiting."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.config import Settings
from bot.rate_limiter import RateLimiter


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
def mock_redis():
    redis = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 0])
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


@pytest.fixture
def rate_limiter(settings, mock_redis):
    return RateLimiter(settings, mock_redis)


class TestRateLimiter:

    @pytest.mark.asyncio
    async def test_allowed_under_limit(self, rate_limiter, mock_redis):
        mock_redis.pipeline.return_value.execute.return_value = [0, 3]
        assert await rate_limiter.check(123) is True

    @pytest.mark.asyncio
    async def test_denied_at_limit(self, rate_limiter, mock_redis):
        mock_redis.pipeline.return_value.execute.return_value = [0, 5]
        assert await rate_limiter.check(123) is False

    @pytest.mark.asyncio
    async def test_denied_over_limit(self, rate_limiter, mock_redis):
        mock_redis.pipeline.return_value.execute.return_value = [0, 10]
        assert await rate_limiter.check(123) is False

    @pytest.mark.asyncio
    async def test_record(self, rate_limiter, mock_redis):
        pipe = mock_redis.pipeline.return_value
        await rate_limiter.record(123)

        pipe.zadd.assert_called_once()
        pipe.expire.assert_called_once()
        pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remaining(self, rate_limiter, mock_redis):
        mock_redis.zcard.return_value = 3
        assert await rate_limiter.get_remaining(123) == 2

    @pytest.mark.asyncio
    async def test_remaining_at_limit(self, rate_limiter, mock_redis):
        mock_redis.zcard.return_value = 5
        assert await rate_limiter.get_remaining(123) == 0

    @pytest.mark.asyncio
    async def test_remaining_over_limit(self, rate_limiter, mock_redis):
        mock_redis.zcard.return_value = 10
        assert await rate_limiter.get_remaining(123) == 0

    @pytest.mark.asyncio
    async def test_key_format(self, rate_limiter):
        assert rate_limiter._key(123) == "rate:123"
        assert rate_limiter._key(456) == "rate:456"
