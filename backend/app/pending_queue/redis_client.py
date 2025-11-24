from typing import Optional

import redis.asyncio as redis

from app.config import Settings


class RedisClient:
    """
    Redis client singleton for managing Redis connections.

    This ensures we reuse the same connection pool across the application.
    """

    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls, settings: Settings) -> redis.Redis:
        """
        Get or create Redis client instance.

        Args:
            settings: Application settings with Redis configuration

        Returns:
            Async Redis client instance
        """
        if cls._instance is None:
            cls._instance = await redis.from_url(
                settings.redis_url,
                decode_responses=True,
                encoding="utf-8",
                max_connections=10,
            )
        return cls._instance

    @classmethod
    async def close(cls) -> None:
        """Close Redis connection"""
        if cls._instance:
            await cls._instance.aclose()
            cls._instance = None
