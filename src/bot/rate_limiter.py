"""Per-user rate limiting using Redis sorted sets (sliding window)."""

import logging
import time

from redis.asyncio import Redis

from bot.config import Settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding window rate limiter backed by Redis sorted sets."""

    KEY_PREFIX = "rate:"

    def __init__(self, settings: Settings, redis: Redis) -> None:
        self._redis = redis
        self._max_requests = settings.rate_limit_per_minute
        self._window_seconds = 60

    def _key(self, user_id: int) -> str:
        return f"{self.KEY_PREFIX}{user_id}"

    async def check(self, user_id: int) -> bool:
        """Return True if the user is within their rate limit."""
        key = self._key(user_id)
        now = time.time()
        window_start = now - self._window_seconds

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        results = await pipe.execute()

        count = results[1]
        if count >= self._max_requests:
            logger.warning(
                "Rate limit exceeded for user %d (%d/%d)",
                user_id, count, self._max_requests,
            )
            return False

        return True

    async def record(self, user_id: int) -> None:
        key = self._key(user_id)
        now = time.time()

        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self._window_seconds + 1)
        await pipe.execute()

    async def get_remaining(self, user_id: int) -> int:
        key = self._key(user_id)
        now = time.time()

        await self._redis.zremrangebyscore(
            key, 0, now - self._window_seconds
        )
        count = await self._redis.zcard(key)
        return max(0, self._max_requests - count)
