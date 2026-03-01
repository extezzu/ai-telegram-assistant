"""Conversation memory management using Redis."""

import json
import logging

from redis.asyncio import Redis

from bot.config import Settings

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Per-user conversation memory backed by Redis.

    Stores the last N messages for each user as a Redis list,
    serialized as JSON strings.
    """

    KEY_PREFIX = "conv:"
    SYSTEM_PREFIX = "sys:"

    def __init__(self, settings: Settings, redis: Redis) -> None:
        self._redis = redis
        self._max_length = settings.max_conversation_length
        self._default_system_prompt = settings.default_system_prompt

    def _conv_key(self, user_id: int) -> str:
        return f"{self.KEY_PREFIX}{user_id}"

    def _sys_key(self, user_id: int) -> str:
        return f"{self.SYSTEM_PREFIX}{user_id}"

    async def add_message(
        self, user_id: int, role: str, content: str
    ) -> None:
        key = self._conv_key(user_id)
        message = json.dumps({"role": role, "content": content})
        await self._redis.rpush(key, message)
        await self._redis.ltrim(key, -self._max_length, -1)

    async def get_messages(self, user_id: int) -> list[dict[str, str]]:
        """Retrieve conversation history with system prompt prepended."""
        system_prompt = await self.get_system_prompt(user_id)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        key = self._conv_key(user_id)
        raw_messages = await self._redis.lrange(key, 0, -1)
        for raw in raw_messages:
            messages.append(json.loads(raw))

        return messages

    async def clear(self, user_id: int) -> None:
        await self._redis.delete(self._conv_key(user_id))
        logger.info("Cleared conversation for user %d", user_id)

    async def set_system_prompt(self, user_id: int, prompt: str) -> None:
        await self._redis.set(self._sys_key(user_id), prompt)

    async def get_system_prompt(self, user_id: int) -> str:
        """Return custom system prompt if set, otherwise the default."""
        prompt = await self._redis.get(self._sys_key(user_id))
        if prompt is not None:
            return prompt if isinstance(prompt, str) else prompt.decode()
        return self._default_system_prompt
