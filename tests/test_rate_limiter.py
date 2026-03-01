"""Tests for rate limiting module."""

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
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 0])
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


@pytest.fixture
def rate_limiter(settings: Settings, mock_redis: AsyncMock) -> RateLimiter:
    return RateLimiter(settings, mock_redis)


class TestRateLimiter:
    """Test RateLimiter behavior."""

    @pytest.mark.asyncio
    async def test_check_allowed(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should allow requests under the limit."""
        pipe = mock_redis.pipeline.return_value
        pipe.execute.return_value = [0, 3]  # 3 requests, limit is 5

        result = await rate_limiter.check(123)
        assert result is True

    @pytest.mark.asyncio
    async def test_check_denied(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should deny requests at the limit."""
        pipe = mock_redis.pipeline.return_value
        pipe.execute.return_value = [0, 5]  # 5 requests, limit is 5

        result = await rate_limiter.check(123)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_over_limit(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should deny requests over the limit."""
        pipe = mock_redis.pipeline.return_value
        pipe.execute.return_value = [0, 10]

        result = await rate_limiter.check(123)
        assert result is False

    @pytest.mark.asyncio
    async def test_record(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should record a request in Redis."""
        pipe = mock_redis.pipeline.return_value

        await rate_limiter.record(123)

        pipe.zadd.assert_called_once()
        pipe.expire.assert_called_once()
        pipe.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_remaining(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should return remaining requests."""
        mock_redis.zcard.return_value = 3

        remaining = await rate_limiter.get_remaining(123)
        assert remaining == 2  # 5 - 3

    @pytest.mark.asyncio
    async def test_get_remaining_at_limit(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should return 0 when at limit."""
        mock_redis.zcard.return_value = 5

        remaining = await rate_limiter.get_remaining(123)
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_get_remaining_over_limit(self, rate_limiter: RateLimiter, mock_redis: AsyncMock) -> None:
        """Should return 0 when over limit."""
        mock_redis.zcard.return_value = 10

        remaining = await rate_limiter.get_remaining(123)
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_key_format(self, rate_limiter: RateLimiter) -> None:
        """Should use correct Redis key format."""
        assert rate_limiter._key(123) == "rate:123"
        assert rate_limiter._key(456) == "rate:456"
