"""Telegram bot command and message handlers."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.ai_client import AIClient, AIClientError
from bot.memory import ConversationMemory
from bot.rate_limiter import RateLimiter
from bot.utils import split_message

logger = logging.getLogger(__name__)

START_MESSAGE = (
    "👋 Hello! I'm an AI assistant powered by GPT-4.\n\n"
    "Just send me a message and I'll respond.\n\n"
    "Commands:\n"
    "/start — Show this message\n"
    "/help — Show help\n"
    "/clear — Clear conversation history\n"
    "/system <prompt> — Set custom system prompt"
)

HELP_MESSAGE = (
    "🤖 *AI Telegram Assistant*\n\n"
    "Send me any message and I'll respond using AI.\n\n"
    "*Commands:*\n"
    "/start — Welcome message\n"
    "/help — This help message\n"
    "/clear — Clear your conversation history\n"
    "/system — Set a custom system prompt\n\n"
    "*Tips:*\n"
    "• I remember our conversation context\n"
    "• Use /clear to start a fresh conversation\n"
    "• Use /system to change my behavior"
)

RATE_LIMIT_MESSAGE = "⏳ You're sending messages too fast. Please wait a moment."
CLEAR_MESSAGE = "🗑 Conversation history cleared."
SYSTEM_USAGE_MESSAGE = (
    "Usage: /system <your custom prompt>\n\n"
    "Example: /system You are a Python expert."
)
SYSTEM_SET_MESSAGE = "✅ System prompt updated."


class Handlers:
    """Container for all bot command and message handlers."""

    def __init__(
        self,
        ai_client: AIClient,
        memory: ConversationMemory,
        rate_limiter: RateLimiter,
    ) -> None:
        self._ai = ai_client
        self._memory = memory
        self._rate_limiter = rate_limiter

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        await update.message.reply_text(START_MESSAGE)

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle the /help command."""
        await update.message.reply_text(HELP_MESSAGE)

    async def clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /clear command."""
        user_id = update.effective_user.id
        await self._memory.clear(user_id)
        await update.message.reply_text(CLEAR_MESSAGE)

    async def system(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /system command to set custom system prompt."""
        if not context.args:
            await update.message.reply_text(SYSTEM_USAGE_MESSAGE)
            return

        prompt = " ".join(context.args)
        user_id = update.effective_user.id
        await self._memory.set_system_prompt(user_id, prompt)
        await update.message.reply_text(SYSTEM_SET_MESSAGE)

    async def message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        user_id = update.effective_user.id
        user_text = update.message.text

        if not user_text:
            return

        # Check rate limit
        allowed = await self._rate_limiter.check(user_id)
        if not allowed:
            await update.message.reply_text(RATE_LIMIT_MESSAGE)
            return

        # Record the request for rate limiting
        await self._rate_limiter.record(user_id)

        # Send typing indicator
        await update.message.chat.send_action("typing")

        # Store user message in memory
        await self._memory.add_message(user_id, "user", user_text)

        # Get conversation history
        messages = await self._memory.get_messages(user_id)

        # Generate AI response
        try:
            response = await self._ai.generate(messages)
        except AIClientError as e:
            logger.error("AI generation failed for user %d: %s", user_id, e)
            await update.message.reply_text(str(e))
            return

        # Store assistant response in memory
        await self._memory.add_message(user_id, "assistant", response.content)

        # Send response (split if too long)
        chunks = split_message(response.content)
        for chunk in chunks:
            await update.message.reply_text(chunk)

        logger.info(
            "User %d — tokens: %d (prompt: %d, completion: %d)",
            user_id,
            response.total_tokens,
            response.prompt_tokens,
            response.completion_tokens,
        )
