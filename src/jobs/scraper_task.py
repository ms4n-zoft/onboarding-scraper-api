"""RQ job function for background product scraping with Redis event persistence."""
from __future__ import annotations

import json
from rq import get_current_job
from loguru import logger

from ..config import load_azure_openai_client
from ..config.redis import get_redis_connection
from ..ai.agentic_analyzer import extract_product_snapshot_agentic
from ..utils.redis_event_emitter import RedisEventEmitter
from ..schemas.events import CompleteEvent, ErrorEvent


def scrape_product_job(source_url: str) -> dict:
    """RQ job function to scrape a product page in the background.

    This function is executed by RQ workers and handles:
    - Redis event persistence for job reconnection
    - Product data extraction using agentic analyzer
    - Error handling and event emission
    - Result storage in Redis

    Args:
        source_url: URL to scrape

    Returns:
        dict with job result metadata including job_id, source_url, and status

    Raises:
        Exception: If scraping fails (RQ will mark job as failed)
    """
    job = get_current_job()
    job_id = job.id

    logger.info(f"Starting scrape job {job_id} for URL: {source_url}")

    # Get Redis connection for event persistence
    redis_client = get_redis_connection()

    # Setup Redis event emitter (no SSE callback for background jobs)
    # Events are persisted to Redis and will be replayed when client reconnects
    emitter = RedisEventEmitter(job_id, redis_client, callback=None)

    try:
        # Load Azure OpenAI client
        client, deployment = load_azure_openai_client()

        # Run scraping with event persistence
        # The agentic analyzer will call emitter callbacks for events
        result = extract_product_snapshot_agentic(
            client,
            deployment,
            source_url,
            event_callback=emitter.emit_event  # Will persist all events to Redis
        )

        # Store result in Redis with 24h expiration
        result_json = result.model_dump_json(indent=2, ensure_ascii=False)
        result_key = f"job:{job_id}:result"
        redis_client.set(result_key, result_json, ex=86400)  # 24h expiration
        logger.info(f"Stored result in Redis for job {job_id}")

        # Emit completion event
        complete_event = CompleteEvent(
            message="All done! Your product information is ready",
            data=result.model_dump()
        )
        emitter.emit_complete(
            message=complete_event.message,
            data=complete_event.data
        )

        logger.info(f"✓ Job {job_id} completed successfully")

        return {
            "job_id": job_id,
            "source_url": source_url,
            "status": "completed",
            "result_stored": True
        }

    except Exception as e:
        logger.error(f"❌ Job {job_id} failed: {str(e)}", exc_info=True)

        # Emit error event
        error_event = ErrorEvent(
            message="Scraping failed",
            error=str(e)
        )
        emitter.emit_error(error_event.message, error_event.error)

        # Re-raise to mark RQ job as failed
        raise
