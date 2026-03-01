"""Tests for conversation memory module."""

import json
from unittest.mock import AsyncMock

import pytest

from bot.config import Settings
from bot.memory import ConversationMemory


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
        default_system_prompt="You are a test assistant.",
        health_check_port=8080,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    return redis


@pytest.fixture
def memory(settings: Settings, mock_redis: AsyncMock) -> ConversationMemory:
    return ConversationMemory(settings, mock_redis)


class TestConversationMemory:
    """Test ConversationMemory operations."""

    @pytest.mark.asyncio
    async def test_add_message(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should store message in Redis list."""
        await memory.add_message(123, "user", "Hello")

        expected_msg = json.dumps({"role": "user", "content": "Hello"})
        mock_redis.rpush.assert_awaited_once_with("conv:123", expected_msg)
        mock_redis.ltrim.assert_awaited_once_with("conv:123", -10, -1)

    @pytest.mark.asyncio
    async def test_get_messages_empty(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should return only system prompt when no messages exist."""
        mock_redis.lrange.return_value = []
        mock_redis.get.return_value = None

        messages = await memory.get_messages(123)

        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a test assistant."

    @pytest.mark.asyncio
    async def test_get_messages_with_history(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should return system prompt + conversation history."""
        mock_redis.lrange.return_value = [
            json.dumps({"role": "user", "content": "Hi"}),
            json.dumps({"role": "assistant", "content": "Hello!"}),
        ]
        mock_redis.get.return_value = None

        messages = await memory.get_messages(456)

        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hi"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_clear(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should delete conversation key from Redis."""
        await memory.clear(123)
        mock_redis.delete.assert_awaited_once_with("conv:123")

    @pytest.mark.asyncio
    async def test_set_system_prompt(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should store custom system prompt."""
        await memory.set_system_prompt(123, "Be a pirate.")
        mock_redis.set.assert_awaited_once_with("sys:123", "Be a pirate.")

    @pytest.mark.asyncio
    async def test_get_system_prompt_custom(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should return custom system prompt when set."""
        mock_redis.get.return_value = "Be a pirate."

        prompt = await memory.get_system_prompt(123)
        assert prompt == "Be a pirate."

    @pytest.mark.asyncio
    async def test_get_system_prompt_default(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should return default system prompt when none set."""
        mock_redis.get.return_value = None

        prompt = await memory.get_system_prompt(123)
        assert prompt == "You are a test assistant."

    @pytest.mark.asyncio
    async def test_get_system_prompt_bytes(self, memory: ConversationMemory, mock_redis: AsyncMock) -> None:
        """Should handle bytes response from Redis."""
        mock_redis.get.return_value = b"Be helpful."

        prompt = await memory.get_system_prompt(123)
        assert prompt == "Be helpful."
