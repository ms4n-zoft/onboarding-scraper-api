"""Dependencies for FastAPI endpoints."""
from __future__ import annotations

from functools import lru_cache
from redis import Redis
from rq import Queue

from .config.redis import get_redis_connection


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Get cached Redis client instance.
    
    Uses LRU cache to maintain a single Redis connection
    instead of creating new connections on each request.
    
    Returns:
        Redis client with connection pooling
    """
    return get_redis_connection()


@lru_cache(maxsize=1)
def get_queue() -> Queue:
    """Get cached RQ queue instance.
    
    Uses LRU cache to maintain a single queue instance
    instead of creating new queues on each request.
    
    Returns:
        RQ Queue for scraping jobs
    """
    redis_client = get_redis_client()
    return Queue("scraper", connection=redis_client)
