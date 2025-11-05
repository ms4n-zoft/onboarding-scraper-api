"""FastAPI application for product scraping and analysis."""
from __future__ import annotations

import json
import time
from typing import AsyncGenerator
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .main import scrape_and_analyze
from .schemas.product import ProductSnapshot
from .schemas.events import CompleteEvent, ErrorEvent
from .config.redis import get_redis_connection
from .jobs.scraper_task import scrape_product_job
from rq import Queue

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


class ScrapeRequest(BaseModel):
    source_url: str = Field(
        ..., 
        description="The URL of the product page to scrape",
        example="https://example.com/product"
    )


class ScrapeResponse(BaseModel):
    success: bool = Field(description="Whether the operation was successful")
    data: ProductSnapshot = Field(description="Extracted product information")
    error: str | None = Field(default=None, description="Error message if operation failed")


class AsyncScrapeResponse(BaseModel):
    """Response for async scrape job submission."""
    job_id: str = Field(description="Unique job identifier for tracking")
    status: str = Field(description="Initial job status (queued)")
    stream_url: str = Field(description="SSE endpoint URL for this job")


# Initialize RQ queue at module level (with lazy connection)
_scrape_queue: Queue | None = None


def get_scrape_queue() -> Queue:
    """Get or initialize the RQ queue for scraping jobs."""
    global _scrape_queue
    if _scrape_queue is None:
        redis_conn = get_redis_connection()
        _scrape_queue = Queue("scraper", connection=redis_conn)
    return _scrape_queue


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
        events_buffer: list[BaseModel] = []

        def event_callback(event: BaseModel) -> None:
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
        queue = get_scrape_queue()
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
