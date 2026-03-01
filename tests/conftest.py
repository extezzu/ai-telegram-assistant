"""Shared test fixtures."""

from unittest.mock import AsyncMock

import pytest

from bot.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Create test settings with dummy values."""
    return Settings(
        telegram_bot_token="test-token",
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        openai_max_tokens=100,
        openai_temperature=0.7,
        redis_url="redis://localhost:6379/0",
        max_conversation_length=10,
        rate_limit_per_minute=5,
        default_system_prompt="You are a test assistant.",
        health_check_port=8080,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    redis = AsyncMock()
    redis.pipeline.return_value = AsyncMock()
    pipe = redis.pipeline.return_value
    pipe.__aenter__ = AsyncMock(return_value=pipe)
    pipe.__aexit__ = AsyncMock(return_value=False)
    pipe.execute = AsyncMock(return_value=[0, 0])
    return redis
