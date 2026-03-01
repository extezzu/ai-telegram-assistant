"""Tests for bot handlers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.ai_client import AIClient, AIClientError, AIResponse
from bot.handlers import (
    CLEAR_MESSAGE,
    HELP_MESSAGE,
    RATE_LIMIT_MESSAGE,
    START_MESSAGE,
    SYSTEM_SET_MESSAGE,
    SYSTEM_USAGE_MESSAGE,
    Handlers,
)
from bot.memory import ConversationMemory
from bot.rate_limiter import RateLimiter


@pytest.fixture
def mock_ai_client():
    client = AsyncMock(spec=AIClient)
    client.generate.return_value = AIResponse(
        content="AI response text",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    return client


@pytest.fixture
def mock_memory():
    memory = AsyncMock(spec=ConversationMemory)
    memory.get_messages.return_value = [
        {"role": "system", "content": "Test prompt."},
        {"role": "user", "content": "Hello"},
    ]
    return memory


@pytest.fixture
def mock_rate_limiter():
    limiter = AsyncMock(spec=RateLimiter)
    limiter.check.return_value = True
    return limiter


@pytest.fixture
def handlers(mock_ai_client, mock_memory, mock_rate_limiter):
    return Handlers(mock_ai_client, mock_memory, mock_rate_limiter)


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_user.id = 123
    update.message.text = "Hello, bot!"
    update.message.reply_text = AsyncMock()
    update.message.chat.send_action = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.args = []
    return ctx


class TestCommands:

    @pytest.mark.asyncio
    async def test_start(self, handlers, mock_update, mock_context):
        await handlers.start(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with(START_MESSAGE)

    @pytest.mark.asyncio
    async def test_help(self, handlers, mock_update, mock_context):
        await handlers.help_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with(HELP_MESSAGE)

    @pytest.mark.asyncio
    async def test_clear(self, handlers, mock_update, mock_context, mock_memory):
        await handlers.clear(mock_update, mock_context)
        mock_memory.clear.assert_awaited_once_with(123)
        mock_update.message.reply_text.assert_awaited_once_with(CLEAR_MESSAGE)

    @pytest.mark.asyncio
    async def test_system_no_args(self, handlers, mock_update, mock_context):
        await handlers.system(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with(SYSTEM_USAGE_MESSAGE)

    @pytest.mark.asyncio
    async def test_system_sets_prompt(self, handlers, mock_update, mock_context, mock_memory):
        mock_context.args = ["Be", "a", "pirate."]
        await handlers.system(mock_update, mock_context)
        mock_memory.set_system_prompt.assert_awaited_once_with(123, "Be a pirate.")
        mock_update.message.reply_text.assert_awaited_once_with(SYSTEM_SET_MESSAGE)


class TestMessageHandler:

    @pytest.mark.asyncio
    async def test_full_flow(self, handlers, mock_update, mock_context, mock_ai_client, mock_memory, mock_rate_limiter):
        await handlers.message(mock_update, mock_context)

        mock_rate_limiter.check.assert_awaited_once_with(123)
        mock_rate_limiter.record.assert_awaited_once_with(123)
        mock_update.message.chat.send_action.assert_awaited_once_with("typing")
        mock_memory.add_message.assert_any_await(123, "user", "Hello, bot!")
        mock_memory.add_message.assert_any_await(123, "assistant", "AI response text")
        mock_update.message.reply_text.assert_awaited_once_with("AI response text")

    @pytest.mark.asyncio
    async def test_rate_limited(self, handlers, mock_update, mock_context, mock_rate_limiter, mock_ai_client):
        mock_rate_limiter.check.return_value = False
        await handlers.message(mock_update, mock_context)

        mock_update.message.reply_text.assert_awaited_once_with(RATE_LIMIT_MESSAGE)
        mock_ai_client.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ai_error(self, handlers, mock_update, mock_context, mock_ai_client):
        mock_ai_client.generate.side_effect = AIClientError("Service unavailable")
        await handlers.message(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with("Service unavailable")

    @pytest.mark.asyncio
    async def test_empty_text_ignored(self, handlers, mock_update, mock_context, mock_ai_client):
        mock_update.message.text = None
        await handlers.message(mock_update, mock_context)
        mock_ai_client.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_long_response_split(self, handlers, mock_update, mock_context, mock_ai_client):
        mock_ai_client.generate.return_value = AIResponse(
            content="a" * 5000,
            prompt_tokens=10,
            completion_tokens=1000,
            total_tokens=1010,
        )
        await handlers.message(mock_update, mock_context)
        assert mock_update.message.reply_text.await_count == 2
