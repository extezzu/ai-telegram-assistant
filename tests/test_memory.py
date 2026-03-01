"""Tests for conversation memory."""

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
    return AsyncMock()


@pytest.fixture
def memory(settings, mock_redis) -> ConversationMemory:
    return ConversationMemory(settings, mock_redis)


class TestConversationMemory:

    @pytest.mark.asyncio
    async def test_add_message(self, memory, mock_redis):
        await memory.add_message(123, "user", "Hello")

        expected = json.dumps({"role": "user", "content": "Hello"})
        mock_redis.rpush.assert_awaited_once_with("conv:123", expected)
        mock_redis.ltrim.assert_awaited_once_with("conv:123", -10, -1)

    @pytest.mark.asyncio
    async def test_get_messages_empty(self, memory, mock_redis):
        mock_redis.lrange.return_value = []
        mock_redis.get.return_value = None

        messages = await memory.get_messages(123)

        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a test assistant."

    @pytest.mark.asyncio
    async def test_get_messages_with_history(self, memory, mock_redis):
        mock_redis.lrange.return_value = [
            json.dumps({"role": "user", "content": "Hi"}),
            json.dumps({"role": "assistant", "content": "Hello!"}),
        ]
        mock_redis.get.return_value = None

        messages = await memory.get_messages(456)

        assert len(messages) == 3
        assert messages[1]["content"] == "Hi"
        assert messages[2]["content"] == "Hello!"

    @pytest.mark.asyncio
    async def test_clear(self, memory, mock_redis):
        await memory.clear(123)
        mock_redis.delete.assert_awaited_once_with("conv:123")

    @pytest.mark.asyncio
    async def test_set_system_prompt(self, memory, mock_redis):
        await memory.set_system_prompt(123, "Be a pirate.")
        mock_redis.set.assert_awaited_once_with(
            "sys:123", "Be a pirate."
        )

    @pytest.mark.asyncio
    async def test_get_custom_system_prompt(self, memory, mock_redis):
        mock_redis.get.return_value = "Be a pirate."
        assert await memory.get_system_prompt(123) == "Be a pirate."

    @pytest.mark.asyncio
    async def test_get_default_system_prompt(self, memory, mock_redis):
        mock_redis.get.return_value = None
        prompt = await memory.get_system_prompt(123)
        assert prompt == "You are a test assistant."

    @pytest.mark.asyncio
    async def test_system_prompt_bytes_decode(self, memory, mock_redis):
        mock_redis.get.return_value = b"Be helpful."
        assert await memory.get_system_prompt(123) == "Be helpful."
