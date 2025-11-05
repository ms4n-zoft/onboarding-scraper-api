# Stage 4: Async Scrape Endpoint - Implementation Summary

## Overview

Added the `/scrape/async` endpoint to FastAPI for submitting background scraping jobs to RQ (Redis Queue).

## Files Modified

### src/api.py

- Added imports for Redis configuration, RQ Queue, and job functions
- Created `AsyncScrapeResponse` Pydantic model for job submission response
- Added `get_scrape_queue()` function for lazy initialization of RQ queue
- Implemented `POST /scrape/async` endpoint

## New Models

### AsyncScrapeResponse

```python
{
    "job_id": "abc-123-def-456",           # Unique job identifier
    "status": "queued",                     # Initial status
    "stream_url": "/jobs/{job_id}/stream"  # SSE endpoint URL
}
```

## New Endpoint

### POST /scrape/async

**Description**: Submit a scraping job to the background queue

**Request**:

```json
{
  "source_url": "https://example.com/product"
}
```

**Response** (200 OK):

```json
{
  "job_id": "abc-123-def-456",
  "status": "queued",
  "stream_url": "/jobs/abc-123-def-456/stream"
}
```

**Error Response** (500 Internal Server Error):

```json
{
  "detail": "Failed to enqueue scraping job: [error message]"
}
```

## Key Features

1. **Job Enqueuing**: Submits job to RQ queue with 10-minute timeout
2. **Lazy Queue Initialization**: RQ queue is initialized on first request
3. **Result Persistence**: Job results stored in Redis with 24-hour TTL
4. **Error Handling**: Comprehensive error handling with proper HTTP status codes
5. **Logging**: Detailed logging for debugging and monitoring

## Queue Configuration

- **Queue Name**: "scraper"
- **Job Timeout**: 600 seconds (10 minutes)
- **Result TTL**: 86400 seconds (24 hours)
- **Failure TTL**: 86400 seconds (24 hours)

## Files Created

### tests/test_async_endpoint.py

Comprehensive test suite covering:

- Job submission and response validation
- Response schema verification
- Multiple job submission
- Job ID uniqueness
- Health endpoint verification
- Queue configuration verification

## Testing Instructions

```bash
# Run the async endpoint test
python tests/test_async_endpoint.py

# Or with pytest
pytest tests/test_async_endpoint.py -v
```

## Integration Points

1. **Redis**: Uses existing Redis configuration (Upstash)
2. **RQ Jobs**: Enqueues `scrape_product_job` function from `src/jobs/scraper_task.py`
3. **Event Emitter**: Job execution will use `RedisEventEmitter` for event persistence
4. **FastAPI**: Integrated with existing FastAPI application

## Next Steps

- Stage 5: Implement `GET /jobs/{job_id}/stream` for SSE streaming with reconnection
- Stage 6: Implement `GET /jobs/{job_id}/status` and `GET /jobs/{job_id}/result`
- Stage 7: Create worker process for running RQ workers
- Stage 8: Integration testing and documentation

## Code Example

```python
import requests

# Submit a scraping job
response = requests.post(
    "http://localhost:8000/scrape/async",
    json={"source_url": "https://example.com"}
)

job_data = response.json()
print(f"Job ID: {job_data['job_id']}")
print(f"Stream URL: {job_data['stream_url']}")

# Later, stream events from the job
stream_url = job_data['stream_url']
stream_response = requests.get(
    f"http://localhost:8000{stream_url}",
    stream=True
)

for line in stream_response.iter_lines():
    if line.startswith(b'data: '):
        event = json.loads(line[6:])
        print(f"Event: {event}")
```

## Commit Message

```
feat: Add async scrape endpoint with RQ job enqueuing (Phase 2 - Stage 4)

- Add POST /scrape/async endpoint for background job submission
- Implement AsyncScrapeResponse model
- Create get_scrape_queue() for lazy RQ queue initialization
- Configure queue with 10-minute timeout and 24-hour result TTL
- Add comprehensive error handling and logging
- Add tests/test_async_endpoint.py with 6 test scenarios
- Update requirements.txt with pytest dependency
```
