"""Per-user rate limiting using Redis."""

import logging
import time

from redis.asyncio import Redis

from bot.config import Settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding window rate limiter backed by Redis.

    Uses Redis sorted sets with timestamps as scores to implement
    a sliding window counter per user.
    """

    KEY_PREFIX = "rate:"

    def __init__(self, settings: Settings, redis: Redis) -> None:
        self._redis = redis
        self._max_requests = settings.rate_limit_per_minute
        self._window_seconds = 60

    def _key(self, user_id: int) -> str:
        """Return the Redis key for a user's rate limit window."""
        return f"{self.KEY_PREFIX}{user_id}"

    async def check(self, user_id: int) -> bool:
        """Check if a user is within their rate limit.

        Cleans up expired entries and checks the count.

        Args:
            user_id: Telegram user ID.

        Returns:
            True if the request is allowed, False if rate limited.
        """
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
        """Record a request for rate limiting.

        Args:
            user_id: Telegram user ID.
        """
        key = self._key(user_id)
        now = time.time()

        pipe = self._redis.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, self._window_seconds + 1)
        await pipe.execute()

    async def get_remaining(self, user_id: int) -> int:
        """Get the number of remaining requests in the current window.

        Args:
            user_id: Telegram user ID.

        Returns:
            Number of requests remaining.
        """
        key = self._key(user_id)
        now = time.time()
        window_start = now - self._window_seconds

        await self._redis.zremrangebyscore(key, 0, window_start)
        count = await self._redis.zcard(key)

        return max(0, self._max_requests - count)
