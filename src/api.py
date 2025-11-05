"""FastAPI application for product scraping and analysis."""
from __future__ import annotations

import json
import time
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from rq.job import Job as RQJob

from .main import scrape_and_analyze
from .schemas.product import ProductSnapshot
from .schemas.events import CompleteEvent, ErrorEvent
from .schemas.api import ScrapeRequest, ScrapeResponse, AsyncScrapeResponse
from .dependencies import get_queue, get_redis_client
from .jobs.scraper_task import scrape_product_job

app = FastAPI(
    title="Product Scraper Engine",
    description="API for scraping and analyzing product information from URLs",
    version="1.0.0",
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests with response time and status code."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.2f}s")
    return response


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_product(request: ScrapeRequest) -> ScrapeResponse:
    try:
        result_json = scrape_and_analyze(request.source_url)
        product_snapshot = ProductSnapshot.model_validate_json(result_json)
        
        return ScrapeResponse(
            success=True,
            data=product_snapshot,
            error=None
        )
    except Exception as e:
        logger.error(f"Scrape failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape and analyze product: {str(e)}"
        )


@app.post("/scrape/stream")
async def scrape_product_stream(request: ScrapeRequest) -> StreamingResponse:
    """Scrape a product page with SSE streaming updates.

    Returns Server-Sent Events (SSE) with progress updates and final result.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events during scraping."""
        events_buffer: list = []

        def event_callback(event) -> None:
            """Buffer events from the scraper."""
            events_buffer.append(event)

        try:
            # Run scraping in thread pool to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()

            async def stream_events():
                """Stream buffered events while scraping runs."""
                scrape_task = loop.run_in_executor(
                    None,
                    scrape_and_analyze,
                    request.source_url,
                    None,
                    event_callback
                )

                # Stream events as they arrive
                last_position = 0
                while not scrape_task.done():
                    await asyncio.sleep(0.1)  # Check for new events every 100ms

                    # Send any new events
                    while last_position < len(events_buffer):
                        event = events_buffer[last_position]
                        yield f"data: {event.model_dump_json()}\n\n"
                        last_position += 1

                # Get the final result
                result_json = await scrape_task
                product_snapshot = ProductSnapshot.model_validate_json(result_json)

                # Send any remaining events
                while last_position < len(events_buffer):
                    event = events_buffer[last_position]
                    yield f"data: {event.model_dump_json()}\n\n"
                    last_position += 1

                # Send completion event with data
                complete_event = CompleteEvent(
                    message="All done! Your product information is ready",
                    data=product_snapshot.model_dump()
                )
                yield f"data: {complete_event.model_dump_json()}\n\n"

            async for event_data in stream_events():
                yield event_data

        except Exception as e:
            logger.error(f"Streaming scrape failed: {str(e)}", exc_info=True)
            error_event = ErrorEvent(
                message="Scraping failed",
                error=str(e)
            )
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "Product Scraper Engine"}


@app.post("/scrape/async", response_model=AsyncScrapeResponse)
async def scrape_product_async(request: ScrapeRequest) -> AsyncScrapeResponse:
    """Submit a scraping job to the background queue.

    Returns immediately with job_id for tracking.
    The job will be processed by RQ workers and results stored in Redis.
    
    Args:
        request: Scrape request with source_url
        
    Returns:
        AsyncScrapeResponse with job_id and stream_url
        
    Raises:
        HTTPException: If job enqueuing fails
    """
    try:
        # Get queue from dependency (cached)
        queue = get_queue()
        
        # Enqueue job with timeout of 600 seconds (10 minutes)
        job = queue.enqueue(
            scrape_product_job,
            args=(request.source_url,),
            job_timeout=600,  # 10 minutes
            result_ttl=86400,  # Keep result for 24h
            failure_ttl=86400,  # Keep failed job info for 24h
        )

        logger.info(f"✓ Enqueued job {job.id} for URL: {request.source_url}")

        return AsyncScrapeResponse(
            job_id=job.id,
            status="queued",
            stream_url=f"/jobs/{job.id}/stream"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to enqueue job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue scraping job: {str(e)}"
        )


@app.get("/jobs/{job_id}/stream")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Stream events for a job with reconnection support.
    
    Returns Server-Sent Events (SSE) with all past events replayed from Redis,
    then continues streaming new events as they arrive.
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        StreamingResponse with text/event-stream
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from Redis and live updates."""
        try:
            redis_client = get_redis_client()
            events_key = f"job:{job_id}:events"
            
            # Get all stored events from Redis
            events_json_list = redis_client.lrange(events_key, 0, -1)
            
            if not events_json_list:
                # Job might not exist or not started yet
                yield f"data: {json.dumps({'event': 'waiting', 'message': 'Waiting for job to start...'})}\n\n"
                await asyncio.sleep(1)
                # Retry once
                events_json_list = redis_client.lrange(events_key, 0, -1)
            
            # Stream all existing events with event IDs for reconnection
            for idx, event_json in enumerate(events_json_list):
                yield f"id: {idx}\n"
                yield f"data: {event_json}\n\n"
            
            # Check job status
            try:
                rq_job = RQJob.fetch(job_id, connection=redis_client)
            except Exception:
                # Job not found in RQ (might be too old, invalid ID, or completed/expired)
                # If we have events in Redis, stream them and close
                if events_json_list:
                    logger.debug(f"Job {job_id} not in RQ registry but has events in Redis (likely completed/expired)")
                    return
                else:
                    logger.warning(f"Job {job_id} not found in RQ or Redis")
                    return
            
            if rq_job.is_finished:
                # Job completed, all events already sent
                logger.info(f"Job {job_id} is finished, closing stream")
                return
            elif rq_job.is_failed:
                # Send error event if not already in events
                error_data = {
                    "event": "error",
                    "message": "Job failed",
                    "error": str(rq_job.exc_info) if rq_job.exc_info else "Unknown error"
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                return
            else:
                # Job still running, poll for new events
                last_position = len(events_json_list)
                poll_count = 0
                max_polls = 6000  # 10 minutes with 0.1s sleep
                
                while poll_count < max_polls:
                    await asyncio.sleep(0.1)
                    poll_count += 1
                    
                    # Get new events since last position
                    new_events = redis_client.lrange(events_key, last_position, -1)
                    
                    if new_events:
                        for idx, event_json in enumerate(new_events):
                            event_id = last_position + idx
                            yield f"id: {event_id}\n"
                            yield f"data: {event_json}\n\n"
                        
                        last_position += len(new_events)
                    
                    # Check if job finished (only every 10 polls to reduce overhead)
                    if poll_count % 10 == 0:
                        rq_job.refresh()
                        if rq_job.is_finished or rq_job.is_failed:
                            logger.info(f"Job {job_id} completed during polling")
                            break
                
                # Final check for any remaining events
                final_events = redis_client.lrange(events_key, last_position, -1)
                for idx, event_json in enumerate(final_events):
                    event_id = last_position + idx
                    yield f"id: {event_id}\n"
                    yield f"data: {event_json}\n\n"
        
        except Exception as e:
            logger.error(f"Error streaming job {job_id}: {str(e)}", exc_info=True)
            error_data = {
                "event": "error",
                "message": "Stream error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
