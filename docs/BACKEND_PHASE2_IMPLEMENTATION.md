# Backend Implementation Guide: Phase 2 (RQ + Redis)

## Overview

This document provides technical implementation details for Phase 2 of the Product Scraper Engine, which introduces Redis Queue (RQ) for background job processing with event persistence and reconnection support.

## Architecture Overview

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  FastAPI     │─────▶│ Redis       │
│  (Browser)  │◀─────│  Server      │◀─────│ (Upstash)   │
└─────────────┘ SSE  └──────────────┘      └─────────────┘
                            │                      ▲
                            │ Enqueue Job          │
                            ▼                      │
                      ┌──────────────┐             │
                      │  RQ Worker   │─────────────┘
                      │  (Process)   │  Store Events
                      └──────────────┘  & Results
```

## Key Components

### 1. Redis Configuration

**File**: `src/config/redis.py`

**Purpose**: Centralized Redis connection management using Upstash Redis.

**Implementation**:
```python
from __future__ import annotations

import os
from redis import Redis
from loguru import logger


def get_redis_connection() -> Redis:
    """Get Redis connection from environment variable.

    Returns:
        Redis client instance

    Raises:
        ValueError: If REDIS_URL is not set
    """
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is required")

    logger.info("Connecting to Redis (Upstash)")
    return Redis.from_url(
        redis_url,
        decode_responses=True,  # Auto-decode bytes to strings
        socket_connect_timeout=5,
        socket_timeout=5,
    )
```

**Caveats**:
- `decode_responses=True` is critical for JSON serialization/deserialization
- Upstash Redis uses TLS (`rediss://`) - ensure URL starts with `rediss://`
- Connection timeout is set to 5 seconds to fail fast
- Consider connection pooling for production (RQ handles this automatically)

---

### 2. Redis Event Emitter

**File**: `src/utils/redis_event_emitter.py`

**Purpose**: Extend EventEmitter to persist events in Redis while maintaining SSE callback support.

**Implementation**:
```python
from __future__ import annotations

import json
from typing import Callable, Any
from redis import Redis
from loguru import logger

from .event_emitter import EventEmitter
from ..schemas.events import StartEvent, ReadingEvent, UpdateEvent


class RedisEventEmitter(EventEmitter):
    """Event emitter that persists events to Redis for job reconnection."""

    def __init__(
        self,
        job_id: str,
        redis_client: Redis,
        callback: Callable[[Any], None] | None = None
    ):
        """Initialize Redis event emitter.

        Args:
            job_id: Unique job identifier
            redis_client: Redis connection
            callback: Optional SSE callback (for real-time streaming)
        """
        super().__init__(callback)
        self.job_id = job_id
        self.redis = redis_client
        self.events_key = f"job:{job_id}:events"

    def _persist_event(self, event: Any) -> None:
        """Persist event to Redis list.

        Args:
            event: Pydantic event model instance
        """
        try:
            event_json = event.model_dump_json()
            self.redis.rpush(self.events_key, event_json)
            # Set expiration to 24 hours (86400 seconds)
            self.redis.expire(self.events_key, 86400)
        except Exception as e:
            logger.error(f"Failed to persist event to Redis: {e}")

    def emit_start(self) -> None:
        """Emit and persist start event."""
        event = StartEvent(message="Checking out your website")
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_update(self, message: str) -> None:
        """Emit and persist update event."""
        event = UpdateEvent(message=message)
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_reading(self, url: str) -> None:
        """Emit and persist reading event."""
        event = ReadingEvent(url=url, message=f"Reading {url}")
        self._persist_event(event)
        if self.callback:
            self.callback(event)
```

**Caveats**:
- **Event Expiration**: Events expire after 24 hours to prevent Redis memory bloat
- **Error Handling**: Event persistence failures are logged but don't stop scraping
- **Atomic Operations**: `rpush` + `expire` is not atomic - use Lua script for production
- **Memory Consideration**: Each event ~200-500 bytes, ~50 events per job = ~25KB per job
- **Key Naming**: Follow pattern `job:{job_id}:events` for consistent namespace

**Production Improvement** (Lua script for atomicity):
```python
def _persist_event_atomic(self, event: Any) -> None:
    """Persist event atomically with expiration."""
    lua_script = """
    redis.call('RPUSH', KEYS[1], ARGV[1])
    redis.call('EXPIRE', KEYS[1], ARGV[2])
    """
    self.redis.eval(lua_script, 1, self.events_key, event.model_dump_json(), 86400)
```

---

### 3. RQ Worker Task

**File**: `src/jobs/scraper_task.py`

**Purpose**: Background job function that executes scraping with Redis event persistence.

**Implementation**:
```python
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
    """RQ job function to scrape a product page.

    Args:
        source_url: URL to scrape

    Returns:
        dict with job result metadata

    Raises:
        Exception: If scraping fails (RQ will mark job as failed)
    """
    job = get_current_job()
    job_id = job.id

    logger.info(f"Starting scrape job {job_id} for URL: {source_url}")

    # Get Redis connection for event persistence
    redis_client = get_redis_connection()

    # Setup Redis event emitter (no SSE callback for background jobs)
    emitter = RedisEventEmitter(job_id, redis_client, callback=None)

    try:
        # Load Azure OpenAI client
        client, deployment = load_azure_openai_client()

        # Run scraping with event persistence
        result = extract_product_snapshot_agentic(
            client,
            deployment,
            source_url,
            event_callback=emitter.emit_event  # Will persist to Redis
        )

        # Store result in Redis
        result_json = result.model_dump_json(indent=2, ensure_ascii=False)
        result_key = f"job:{job_id}:result"
        redis_client.set(result_key, result_json, ex=86400)  # 24h expiration

        # Emit completion event
        complete_event = CompleteEvent(
            message="All done! Your product information is ready",
            data=result.model_dump()
        )
        emitter._persist_event(complete_event)

        logger.info(f"Job {job_id} completed successfully")

        return {
            "job_id": job_id,
            "source_url": source_url,
            "status": "completed",
            "result_stored": True
        }

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

        # Emit error event
        error_event = ErrorEvent(
            message="Scraping failed",
            error=str(e)
        )
        emitter._persist_event(error_event)

        # Re-raise to mark RQ job as failed
        raise
```

**Caveats**:
- **Job Context**: Must use `get_current_job()` inside the job function, not at module level
- **Exception Handling**: Re-raising exceptions marks job as failed in RQ (desired behavior)
- **Event Callback**: Need to create a wrapper method in RedisEventEmitter to handle generic events
- **Result Storage**: Both RQ and custom Redis storage for 24h - consider cleanup jobs
- **Timeouts**: Default RQ timeout is 180s - increase for long scraping jobs
- **Redis Connection**: Each job creates its own connection - RQ handles cleanup

**Event Callback Wrapper** (add to RedisEventEmitter):
```python
def emit_event(self, event: Any) -> None:
    """Generic event emitter for callback compatibility."""
    self._persist_event(event)
    if self.callback:
        self.callback(event)
```

---

### 4. FastAPI Async Endpoints

**File**: `src/api.py` (additions)

**New Endpoints**:

#### 4.1. POST /scrape/async - Submit Scraping Job

```python
from rq import Queue
from rq.job import Job
from .config.redis import get_redis_connection
from .jobs.scraper_task import scrape_product_job


# Initialize RQ queue (module level)
redis_conn = get_redis_connection()
scrape_queue = Queue("scraper", connection=redis_conn)


class AsyncScrapeResponse(BaseModel):
    job_id: str = Field(description="Unique job identifier for tracking")
    status: str = Field(description="Initial job status (queued)")
    stream_url: str = Field(description="SSE endpoint URL for this job")


@app.post("/scrape/async", response_model=AsyncScrapeResponse)
async def scrape_product_async(request: ScrapeRequest) -> AsyncScrapeResponse:
    """Submit a scraping job to the background queue.

    Returns immediately with job_id for tracking.
    """
    try:
        # Enqueue job with timeout of 600 seconds (10 minutes)
        job = scrape_queue.enqueue(
            scrape_product_job,
            args=(request.source_url,),
            job_timeout=600,
            result_ttl=86400,  # Keep result for 24h
            failure_ttl=86400,  # Keep failed job info for 24h
        )

        logger.info(f"Enqueued job {job.id} for URL: {request.source_url}")

        return AsyncScrapeResponse(
            job_id=job.id,
            status="queued",
            stream_url=f"/jobs/{job.id}/stream"
        )
    except Exception as e:
        logger.error(f"Failed to enqueue job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enqueue scraping job: {str(e)}"
        )
```

**Caveats**:
- **Job Timeout**: Set to 600s (10 min) - adjust based on average scraping time
- **TTL Settings**: `result_ttl` and `failure_ttl` should match Redis event expiration
- **Queue Initialization**: Initialize queue at module level, not per-request
- **Job ID Format**: RQ generates UUIDs - predictable for frontend usage

---

#### 4.2. GET /jobs/{job_id}/stream - SSE Stream with Reconnection

```python
from rq.job import Job as RQJob


@app.get("/jobs/{job_id}/stream")
async def stream_job_events(job_id: str) -> StreamingResponse:
    """Stream events for a job with reconnection support.

    Supports Last-Event-ID header for resuming from last received event.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            redis_client = get_redis_connection()
            events_key = f"job:{job_id}:events"

            # Get all stored events
            events_json_list = redis_client.lrange(events_key, 0, -1)

            if not events_json_list:
                # Job might not exist or not started yet
                yield f"data: {json.dumps({'event': 'waiting', 'message': 'Waiting for job to start...'})}\n\n"
                await asyncio.sleep(1)
                # Retry once
                events_json_list = redis_client.lrange(events_key, 0, -1)

            # Stream all events
            for idx, event_json in enumerate(events_json_list):
                yield f"id: {idx}\n"
                yield f"data: {event_json}\n\n"

            # Check if job is complete
            rq_job = RQJob.fetch(job_id, connection=redis_client)

            if rq_job.is_finished:
                # Job completed, no more events
                return
            elif rq_job.is_failed:
                # Send error event if not already in events
                error_event = ErrorEvent(
                    message="Job failed",
                    error=str(rq_job.exc_info) if rq_job.exc_info else "Unknown error"
                )
                yield f"data: {error_event.model_dump_json()}\n\n"
                return
            else:
                # Job still running, poll for new events
                last_position = len(events_json_list)
                poll_count = 0
                max_polls = 600  # 60 seconds with 0.1s sleep

                while poll_count < max_polls:
                    await asyncio.sleep(0.1)
                    poll_count += 1

                    # Get new events
                    new_events = redis_client.lrange(events_key, last_position, -1)

                    for idx, event_json in enumerate(new_events):
                        event_id = last_position + idx
                        yield f"id: {event_id}\n"
                        yield f"data: {event_json}\n\n"

                    last_position += len(new_events)

                    # Check if job finished
                    rq_job.refresh()
                    if rq_job.is_finished or rq_job.is_failed:
                        break

        except Exception as e:
            logger.error(f"Error streaming job {job_id}: {str(e)}", exc_info=True)
            error_event = ErrorEvent(
                message="Stream error",
                error=str(e)
            )
            yield f"data: {error_event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
```

**Caveats**:
- **Reconnection**: SSE `Last-Event-ID` header support requires parsing and resuming from that position
- **Polling Timeout**: 60s max poll time prevents infinite streams
- **Job Refresh**: `rq_job.refresh()` is expensive - only call when checking completion
- **Race Condition**: Events written between checks might be missed - use Redis BLPOP for production
- **Memory**: Loading all events with `lrange(0, -1)` can be expensive for long jobs

**Production Improvement** (Last-Event-ID support):
```python
from fastapi import Header

@app.get("/jobs/{job_id}/stream")
async def stream_job_events(
    job_id: str,
    last_event_id: str | None = Header(None, alias="Last-Event-ID")
) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        # Start from last received event if reconnecting
        start_position = int(last_event_id) + 1 if last_event_id else 0

        redis_client = get_redis_connection()
        events_key = f"job:{job_id}:events"

        # Get events from start_position onwards
        events_json_list = redis_client.lrange(events_key, start_position, -1)

        for idx, event_json in enumerate(events_json_list):
            event_id = start_position + idx
            yield f"id: {event_id}\n"
            yield f"data: {event_json}\n\n"

        # Continue polling...
```

---

#### 4.3. GET /jobs/{job_id}/status - Job Status Check

```python
class JobStatus(BaseModel):
    job_id: str
    status: str  # queued, started, finished, failed
    progress: int | None = None  # Percentage if available
    enqueued_at: str | None = None
    started_at: str | None = None
    ended_at: str | None = None


@app.get("/jobs/{job_id}/status", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """Get current status of a scraping job."""
    try:
        redis_client = get_redis_connection()
        rq_job = RQJob.fetch(job_id, connection=redis_client)

        # Map RQ status to our status
        status_map = {
            "queued": "queued",
            "started": "started",
            "finished": "finished",
            "failed": "failed",
            "deferred": "queued",
            "scheduled": "queued",
        }

        return JobStatus(
            job_id=job_id,
            status=status_map.get(rq_job.get_status(), "unknown"),
            enqueued_at=rq_job.enqueued_at.isoformat() if rq_job.enqueued_at else None,
            started_at=rq_job.started_at.isoformat() if rq_job.started_at else None,
            ended_at=rq_job.ended_at.isoformat() if rq_job.ended_at else None,
        )
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )
```

**Caveats**:
- **Job Expiry**: Jobs expire after 24h - returns 404 for expired jobs
- **Status Mapping**: RQ has more statuses than we expose - map carefully
- **Datetime Serialization**: Use `.isoformat()` for consistent format
- **Progress Tracking**: Not implemented yet - would require custom metadata

---

#### 4.4. GET /jobs/{job_id}/result - Get Final Result

```python
@app.get("/jobs/{job_id}/result", response_model=ScrapeResponse)
async def get_job_result(job_id: str) -> ScrapeResponse:
    """Get the final result of a completed scraping job."""
    try:
        redis_client = get_redis_connection()

        # Check job status
        rq_job = RQJob.fetch(job_id, connection=redis_client)

        if not rq_job.is_finished:
            raise HTTPException(
                status_code=400,
                detail=f"Job {job_id} is not finished yet (status: {rq_job.get_status()})"
            )

        # Get result from Redis
        result_key = f"job:{job_id}:result"
        result_json = redis_client.get(result_key)

        if not result_json:
            raise HTTPException(
                status_code=404,
                detail=f"Result for job {job_id} not found (may have expired)"
            )

        product_snapshot = ProductSnapshot.model_validate_json(result_json)

        return ScrapeResponse(
            success=True,
            data=product_snapshot,
            error=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job result: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve job result: {str(e)}"
        )
```

**Caveats**:
- **Result Availability**: Only available after job completion
- **Expiration**: Results expire after 24h - document this clearly
- **Duplicate Storage**: Result stored in both RQ and custom Redis key
- **Failed Jobs**: Should return error message from RQ job metadata

---

### 5. RQ Worker Setup

**File**: `worker.py` (project root)

```python
"""RQ worker for processing scraping jobs."""
from __future__ import annotations

from rq import Worker, Queue, Connection
from loguru import logger

from src.config.redis import get_redis_connection
from src.utils.logging import configure_logging


def main():
    """Start RQ worker for scraper queue."""
    configure_logging(level="INFO")

    redis_conn = get_redis_connection()

    with Connection(redis_conn):
        worker = Worker(
            ["scraper"],  # Queue name
            name="scraper-worker",
            connection=redis_conn,
        )

        logger.info("Starting RQ worker for 'scraper' queue")
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
```

**Running the Worker**:
```bash
# Development
python worker.py

# Production (with process management)
rq worker scraper --url $REDIS_URL --name scraper-worker-1
```

**Caveats**:
- **Single Process**: One worker processes one job at a time
- **Scaling**: Run multiple worker processes for parallelism
- **Monitoring**: Use RQ dashboard or custom monitoring
- **Graceful Shutdown**: Workers handle SIGTERM gracefully
- **Logging**: Ensure worker logs are captured (stdout/stderr)

---

## Critical Caveats and Considerations

### 1. Redis Memory Management

**Problem**: Events and results accumulate in Redis over time.

**Solutions**:
- ✅ Set 24h TTL on all keys (`ex=86400`)
- ✅ Use Redis `EXPIRE` command on event lists
- ⚠️ Consider cleanup job for orphaned keys
- ⚠️ Monitor Redis memory usage (Upstash has limits)

**Cleanup Job** (optional):
```python
# Run daily via cron or RQ scheduler
def cleanup_expired_jobs():
    """Remove job keys older than 24h."""
    redis_client = get_redis_connection()
    cursor = 0

    while True:
        cursor, keys = redis_client.scan(
            cursor,
            match="job:*:events",
            count=100
        )

        for key in keys:
            ttl = redis_client.ttl(key)
            if ttl == -1:  # No expiration set
                redis_client.expire(key, 86400)

        if cursor == 0:
            break
```

---

### 2. Event Ordering and Atomicity

**Problem**: `rpush` + `expire` is not atomic - race conditions possible.

**Solution**: Use Lua scripts for atomic operations (shown earlier).

**Alternative**: Accept eventual consistency - expiration races are non-critical.

---

### 3. Worker Scaling and Job Distribution

**Problem**: Single worker = single job at a time = slow.

**Solutions**:
- Run multiple worker processes (3-5 for CPU-bound work)
- Use worker pools with `--burst` flag for auto-scaling
- Monitor queue length and scale workers dynamically

**Multi-Worker Setup**:
```bash
# Terminal 1
rq worker scraper --url $REDIS_URL --name worker-1

# Terminal 2
rq worker scraper --url $REDIS_URL --name worker-2

# Terminal 3
rq worker scraper --url $REDIS_URL --name worker-3
```

**Production (Supervisor)**:
```ini
[program:rq-worker]
command=/path/to/venv/bin/rq worker scraper --url %(ENV_REDIS_URL)s
process_name=%(program_name)s-%(process_num)s
numprocs=3
autostart=true
autorestart=true
```

---

### 4. SSE Reconnection Edge Cases

**Problem**: Client reconnects during event emission - might miss events.

**Solution**: Use `Last-Event-ID` header to resume from last received event.

**Implementation**: See "Production Improvement" in section 4.2.

---

### 5. Job Timeout Configuration

**Problem**: Some sites take >10 minutes to scrape (many pages, slow responses).

**Solutions**:
- Increase `job_timeout` parameter when enqueuing
- Monitor average job duration and adjust
- Implement job heartbeat/progress updates

**Dynamic Timeout**:
```python
# Estimate timeout based on URL complexity
def estimate_timeout(url: str) -> int:
    """Estimate scraping timeout based on domain."""
    # Simple heuristic - adjust based on metrics
    if "complex-site.com" in url:
        return 1200  # 20 minutes
    return 600  # 10 minutes (default)

job = scrape_queue.enqueue(
    scrape_product_job,
    args=(request.source_url,),
    job_timeout=estimate_timeout(request.source_url),
)
```

---

### 6. Error Handling and Job Retries

**Problem**: Transient failures (network issues, API rate limits) should be retried.

**Solution**: Configure RQ retry policies.

**Implementation**:
```python
from rq import Retry

job = scrape_queue.enqueue(
    scrape_product_job,
    args=(request.source_url,),
    retry=Retry(max=3, interval=[60, 120, 300]),  # 1min, 2min, 5min backoff
)
```

**Caveats**:
- Retries consume worker capacity
- Failed jobs still count toward failure_ttl
- Consider exponential backoff for rate limits

---

### 7. Redis Connection Pool Exhaustion

**Problem**: Each request creates a Redis connection - pool exhaustion under load.

**Solution**: Reuse Redis connection via dependency injection.

**Implementation**:
```python
from functools import lru_cache

@lru_cache
def get_redis_client() -> Redis:
    """Cached Redis client with connection pooling."""
    return get_redis_connection()

# In endpoints
redis_client = get_redis_client()
```

**Better Solution** (FastAPI dependency):
```python
from fastapi import Depends

def get_redis() -> Redis:
    """FastAPI dependency for Redis connection."""
    return get_redis_client()

@app.get("/jobs/{job_id}/status")
async def get_job_status(
    job_id: str,
    redis: Redis = Depends(get_redis)
) -> JobStatus:
    rq_job = RQJob.fetch(job_id, connection=redis)
    # ...
```

---

### 8. Monitoring and Observability

**Required Metrics**:
- Queue length (jobs waiting)
- Active workers count
- Job success/failure rate
- Average job duration
- Redis memory usage

**Tools**:
- **RQ Dashboard**: Web UI for monitoring (`rq-dashboard --redis-url $REDIS_URL`)
- **Prometheus + Grafana**: Export RQ metrics
- **Datadog/New Relic**: APM integration

**Custom Metrics Endpoint**:
```python
@app.get("/metrics/queue")
async def queue_metrics() -> dict:
    """Get queue metrics for monitoring."""
    redis_client = get_redis_connection()
    queue = Queue("scraper", connection=redis_client)

    return {
        "queue_length": len(queue),
        "started_jobs": queue.started_job_registry.count,
        "finished_jobs": queue.finished_job_registry.count,
        "failed_jobs": queue.failed_job_registry.count,
        "workers_count": Worker.count(connection=redis_client),
    }
```

---

### 9. Security Considerations

**Authentication**: No auth in current implementation - add API keys/JWT.

**Rate Limiting**: Prevent abuse with Redis-based rate limiting.

**Input Validation**: Validate URLs to prevent SSRF attacks.

**Implementation**:
```python
from urllib.parse import urlparse

def validate_url(url: str) -> bool:
    """Validate URL to prevent SSRF."""
    parsed = urlparse(url)

    # Block private IPs
    if parsed.hostname in ["localhost", "127.0.0.1", "0.0.0.0"]:
        return False

    # Only allow http/https
    if parsed.scheme not in ["http", "https"]:
        return False

    return True

@app.post("/scrape/async")
async def scrape_product_async(request: ScrapeRequest):
    if not validate_url(request.source_url):
        raise HTTPException(status_code=400, detail="Invalid URL")
    # ...
```

---

### 10. Testing Strategy

**Unit Tests**:
- Test RedisEventEmitter persistence
- Test event serialization/deserialization
- Mock Redis connections

**Integration Tests**:
- Test full job lifecycle (enqueue → process → retrieve)
- Test SSE streaming with mock Redis
- Test reconnection with Last-Event-ID

**Load Tests**:
- Simulate multiple concurrent jobs
- Test worker scaling behavior
- Monitor Redis memory under load

**Example Test**:
```python
import pytest
from fakeredis import FakeRedis

def test_redis_event_emitter():
    """Test event persistence in Redis."""
    fake_redis = FakeRedis(decode_responses=True)
    job_id = "test-job-123"

    emitter = RedisEventEmitter(job_id, fake_redis)
    emitter.emit_start()

    # Verify event stored
    events = fake_redis.lrange(f"job:{job_id}:events", 0, -1)
    assert len(events) == 1

    event_data = json.loads(events[0])
    assert event_data["event"] == "start"
```

---

## Deployment Checklist

- [ ] Set `REDIS_URL` environment variable
- [ ] Install dependencies: `pip install rq redis`
- [ ] Test Redis connection: `python -c "from src.config.redis import get_redis_connection; get_redis_connection()"`
- [ ] Start RQ worker(s): `rq worker scraper --url $REDIS_URL`
- [ ] Start FastAPI server: `uvicorn src.api:app --host 0.0.0.0 --port 8000`
- [ ] Verify health endpoint: `curl http://localhost:8000/health`
- [ ] Submit test job: `curl -X POST http://localhost:8000/scrape/async -H "Content-Type: application/json" -d '{"source_url": "https://example.com"}'`
- [ ] Monitor RQ dashboard: `rq-dashboard --redis-url $REDIS_URL` (visit http://localhost:9181)
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation (e.g., CloudWatch, ELK)
- [ ] Set up worker auto-scaling (Kubernetes HPA, AWS ECS, etc.)

---

## Migration from Phase 1

**Backward Compatibility**: Keep `/scrape/stream` endpoint for real-time use cases.

**New Endpoints**: Add async endpoints without breaking existing clients.

**Frontend Migration**:
1. Update to use `/scrape/async` for new requests
2. Implement job_id persistence in localStorage
3. Add reconnection logic using `Last-Event-ID`
4. Fall back to `/scrape/stream` if job_id not found

**Gradual Rollout**:
- Week 1: Deploy Phase 2 endpoints alongside Phase 1
- Week 2: Update frontend to use Phase 2 for new users
- Week 3: Monitor metrics and adjust worker count
- Week 4: Deprecation notice for Phase 1 (optional)

---

## Future Improvements

1. **Progress Tracking**: Emit progress percentage based on pages fetched
2. **Job Prioritization**: Use multiple queues (high/normal/low priority)
3. **Result Caching**: Cache results by URL hash to avoid re-scraping
4. **Webhook Notifications**: Notify external systems on job completion
5. **Batch Processing**: Accept multiple URLs in single request
6. **Custom Timeouts**: Let clients specify timeout per job
7. **Job Cancellation**: Allow clients to cancel running jobs
8. **Event Replay**: Replay events from any position (not just last)

---

## Support and Troubleshooting

**Common Issues**:

| Issue | Cause | Solution |
|-------|-------|----------|
| "Job not found" | Job expired (>24h) | Reduce TTL or increase caching |
| SSE connection drops | Nginx/proxy timeout | Add keep-alive headers, increase proxy timeout |
| Workers not processing | Worker crashed/stopped | Check worker logs, restart worker |
| Slow job processing | Not enough workers | Scale up worker count |
| Redis memory full | Too many jobs/events | Enable eviction policy, cleanup old jobs |

**Debug Commands**:
```bash
# Check queue status
rq info --url $REDIS_URL

# List all jobs
rq info --url $REDIS_URL --by-queue

# Inspect specific job
redis-cli -u $REDIS_URL --eval "return redis.call('lrange', 'rq:job:JOB_ID', 0, -1)"

# Monitor Redis memory
redis-cli -u $REDIS_URL info memory
```

---

## Conclusion

Phase 2 introduces robust job processing with reconnection support, enabling a production-ready scraping service. Follow this guide carefully, paying special attention to the caveats and best practices outlined above.

For questions or issues, contact the backend team lead.
