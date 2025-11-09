#!/usr/bin/env python3
"""Clear all jobs from the Redis queue.

Usage:
    python clear_queue.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from loguru import logger
from rq import Queue

from src.config.redis import get_redis_connection

load_dotenv()

# Configure simple logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def clear_queue():
    """Clear all jobs from the scraper queue."""
    logger.info("Connecting to Redis...")
    redis_conn = get_redis_connection(decode_responses=False)
    
    queue = Queue("scraper", connection=redis_conn)
    
    initial_count = len(queue)
    logger.info(f"Found {initial_count} jobs in queue")
    
    if initial_count == 0:
        logger.info("Queue is already empty!")
        return
    
    # Empty the queue
    logger.info("Clearing queue...")
    queue.empty()
    
    # Also clear failed jobs
    failed_count = queue.failed_job_registry.count
    if failed_count > 0:
        logger.info(f"Found {failed_count} failed jobs")
        logger.info("Clearing failed jobs...")
        for job_id in queue.failed_job_registry.get_job_ids():
            queue.failed_job_registry.remove(job_id, delete_job=True)
    
    final_count = len(queue)
    logger.success(f"✓ Queue cleared! ({initial_count} → {final_count} jobs)")


if __name__ == "__main__":
    try:
        clear_queue()
    except KeyboardInterrupt:
        logger.info("\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
