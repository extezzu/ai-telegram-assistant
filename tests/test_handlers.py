"""Tests for bot command and message handlers."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.ai_client import AIClient, AIClientError, AIResponse
from bot.config import Settings
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
def mock_ai_client() -> AsyncMock:
    client = AsyncMock(spec=AIClient)
    client.generate.return_value = AIResponse(
        content="AI response text",
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
    )
    return client


@pytest.fixture
def mock_memory() -> AsyncMock:
    memory = AsyncMock(spec=ConversationMemory)
    memory.get_messages.return_value = [
        {"role": "system", "content": "Test prompt."},
        {"role": "user", "content": "Hello"},
    ]
    return memory


@pytest.fixture
def mock_rate_limiter() -> AsyncMock:
    limiter = AsyncMock(spec=RateLimiter)
    limiter.check.return_value = True
    return limiter


@pytest.fixture
def handlers(
    mock_ai_client: AsyncMock,
    mock_memory: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> Handlers:
    return Handlers(mock_ai_client, mock_memory, mock_rate_limiter)


@pytest.fixture
def mock_update() -> MagicMock:
    update = MagicMock()
    update.effective_user.id = 123
    update.message.text = "Hello, bot!"
    update.message.reply_text = AsyncMock()
    update.message.chat.send_action = AsyncMock()
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.args = []
    return context


class TestStartCommand:
    """Test /start command handler."""

    @pytest.mark.asyncio
    async def test_start_sends_welcome(
        self, handlers: Handlers, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        await handlers.start(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with(START_MESSAGE)


class TestHelpCommand:
    """Test /help command handler."""

    @pytest.mark.asyncio
    async def test_help_sends_message(
        self, handlers: Handlers, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        await handlers.help_command(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with(HELP_MESSAGE)


class TestClearCommand:
    """Test /clear command handler."""

    @pytest.mark.asyncio
    async def test_clear_clears_memory(
        self, handlers: Handlers, mock_update: MagicMock, mock_context: MagicMock, mock_memory: AsyncMock
    ) -> None:
        await handlers.clear(mock_update, mock_context)
        mock_memory.clear.assert_awaited_once_with(123)
        mock_update.message.reply_text.assert_awaited_once_with(CLEAR_MESSAGE)


class TestSystemCommand:
    """Test /system command handler."""

    @pytest.mark.asyncio
    async def test_system_no_args(
        self, handlers: Handlers, mock_update: MagicMock, mock_context: MagicMock
    ) -> None:
        mock_context.args = []
        await handlers.system(mock_update, mock_context)
        mock_update.message.reply_text.assert_awaited_once_with(SYSTEM_USAGE_MESSAGE)

    @pytest.mark.asyncio
    async def test_system_sets_prompt(
        self, handlers: Handlers, mock_update: MagicMock, mock_context: MagicMock, mock_memory: AsyncMock
    ) -> None:
        mock_context.args = ["Be", "a", "pirate."]
        await handlers.system(mock_update, mock_context)
        mock_memory.set_system_prompt.assert_awaited_once_with(123, "Be a pirate.")
        mock_update.message.reply_text.assert_awaited_once_with(SYSTEM_SET_MESSAGE)


class TestMessageHandler:
    """Test message handler."""

    @pytest.mark.asyncio
    async def test_message_success(
        self,
        handlers: Handlers,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_ai_client: AsyncMock,
        mock_memory: AsyncMock,
        mock_rate_limiter: AsyncMock,
    ) -> None:
        await handlers.message(mock_update, mock_context)

        mock_rate_limiter.check.assert_awaited_once_with(123)
        mock_rate_limiter.record.assert_awaited_once_with(123)
        mock_update.message.chat.send_action.assert_awaited_once_with("typing")
        mock_memory.add_message.assert_any_await(123, "user", "Hello, bot!")
        mock_memory.add_message.assert_any_await(123, "assistant", "AI response text")
        mock_update.message.reply_text.assert_awaited_once_with("AI response text")

    @pytest.mark.asyncio
    async def test_message_rate_limited(
        self,
        handlers: Handlers,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_rate_limiter: AsyncMock,
        mock_ai_client: AsyncMock,
    ) -> None:
        mock_rate_limiter.check.return_value = False

        await handlers.message(mock_update, mock_context)

        mock_update.message.reply_text.assert_awaited_once_with(RATE_LIMIT_MESSAGE)
        mock_ai_client.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_message_ai_error(
        self,
        handlers: Handlers,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_ai_client: AsyncMock,
    ) -> None:
        mock_ai_client.generate.side_effect = AIClientError("Service unavailable")

        await handlers.message(mock_update, mock_context)

        mock_update.message.reply_text.assert_awaited_once_with("Service unavailable")

    @pytest.mark.asyncio
    async def test_message_empty_text(
        self,
        handlers: Handlers,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_ai_client: AsyncMock,
    ) -> None:
        mock_update.message.text = None

        await handlers.message(mock_update, mock_context)

        mock_ai_client.generate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_message_long_response_split(
        self,
        handlers: Handlers,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_ai_client: AsyncMock,
    ) -> None:
        long_text = "a" * 5000
        mock_ai_client.generate.return_value = AIResponse(
            content=long_text,
            prompt_tokens=10,
            completion_tokens=1000,
            total_tokens=1010,
        )

        await handlers.message(mock_update, mock_context)

        assert mock_update.message.reply_text.await_count == 2
