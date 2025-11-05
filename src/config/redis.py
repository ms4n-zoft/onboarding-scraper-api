"""Redis configuration and connection management."""
from __future__ import annotations

from redis import Redis
from loguru import logger

from ..utils.env import get_required_env_var


def get_redis_connection() -> Redis:
    """Get Redis connection from environment variable.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If REDIS_URL is not set
    """
    redis_url = get_required_env_var("REDIS_URL")

    logger.info("Connecting to Redis (Upstash)")
    return Redis.from_url(
        redis_url,
        decode_responses=True,  # Auto-decode bytes to strings
        socket_connect_timeout=5,
        socket_timeout=5,
    )
