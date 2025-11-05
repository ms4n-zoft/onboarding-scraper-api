"""Redis configuration and connection management."""
from __future__ import annotations

from redis import Redis
from loguru import logger

from ..utils.env import get_required_env_var


def get_redis_connection(decode_responses: bool = True) -> Redis:
    """Get Redis connection from environment variable.

    Args:
        decode_responses: Whether to decode responses to strings.
                         Set to False for RQ (which uses pickled data).
                         Set to True for JSON data.

    Returns:
        Redis client instance

    Raises:
        RuntimeError: If REDIS_URL is not set
    """
    redis_url = get_required_env_var("REDIS_URL")

    logger.info(f"Connecting to Redis (Upstash) with decode_responses={decode_responses}")
    return Redis.from_url(
        redis_url,
        decode_responses=decode_responses,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
