# Product Scraper (Prototype)

Minimal Python prototype for experimenting with agentic scraping backed by Azure OpenAI. Given a starting URL, the script fetches the page, strips boilerplate, and asks an LLM to structure product-related insights.

## Prerequisites

- Python 3.11+
- Azure OpenAI resource with a model deployment (e.g. `gpt-5-mini`)

## Setup

1. Clone or open this repo. Optionally create a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure Azure OpenAI credentials (see `.env.example`). Either export the variables or copy the file to `.env` and fill in values.

## Usage

### CLI Mode

```bash
python -m src.main https://www.leadspace.com/
```

The script prints structured JSON with extracted details. Use `--out <path>` to persist the JSON to disk.

### FastAPI Server

To run the API server:

```bash
python -m uvicorn src.api:app --reload
```

The server will start on `http://localhost:8000`.

#### API Endpoints

**Health Check**

```
GET /health
```

**Synchronous Scrape (Blocking)**

```
POST /scrape
```

Request body:

```json
{
  "source_url": "https://www.leadspace.com/"
}
```

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"source_url": "https://www.leadspace.com/"}'
```

Response:

```json
{
  "success": true,
  "data": {
    "product_name": "...",
    "company_name": "...",
    "website": "...",
    "overview": "...",
    ...
  },
  "error": null
}
```

**Async Scrape (Background Job)**

```
POST /scrape/async
```

Submits a scraping job to the background queue and returns immediately.

Request body:

```json
{
  "source_url": "https://www.leadspace.com/"
}
```

Response:

```json
{
  "job_id": "abc123-def456-...",
  "status": "queued",
  "stream_url": "/jobs/abc123-def456-.../stream"
}
```

**Stream Job Events (Server-Sent Events)**

```
GET /jobs/{job_id}/stream
```

Stream real-time events from a background job using SSE.

```bash
curl -N http://localhost:8000/jobs/abc123-def456-.../stream
```

Events include: `start`, `reading`, `update`, `complete`, `error`

**Get Job Status**

```
GET /jobs/{job_id}/status
```

Get the current status and metadata of a background job.

Response:

```json
{
  "job_id": "abc123-def456-...",
  "status": "finished",
  "enqueued_at": "2025-11-05T12:00:00Z",
  "started_at": "2025-11-05T12:00:05Z",
  "ended_at": "2025-11-05T12:00:30Z",
  "position": null
}
```

**Get Job Result**

```
GET /jobs/{job_id}/result
```

Retrieve the result of a completed background job.

Response:

```json
{
  "job_id": "abc123-def456-...",
  "status": "finished",
  "result": {
    "product_name": "...",
    "company_name": "...",
    ...
  },
  "error": null
}
```

#### Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI documentation or `http://localhost:8000/redoc` for ReDoc documentation.

### Background Workers (RQ)

For background job processing, you need to run RQ workers separately from the API server.

#### Starting a Worker

Basic usage:

```bash
python worker.py
```

With custom configuration:

```bash
# Custom worker name
RQ_WORKER_NAME=worker-1 python worker.py

# Burst mode (process all jobs then exit)
RQ_WORKER_BURST=true python worker.py
```

#### Worker Logs

Worker logs are stored in the `logs/` directory with daily rotation:

- `logs/worker_YYYY-MM-DD.log` - Daily log files (kept for 30 days)
- Console output with colored formatting

#### Production Deployment

For production, run multiple workers:

```bash
# Terminal 1 - API Server
uvicorn src.api:app --host 0.0.0.0 --port 8000 --workers 4

# Terminal 2 - Worker 1
RQ_WORKER_NAME=worker-1 python worker.py

# Terminal 3 - Worker 2
RQ_WORKER_NAME=worker-2 python worker.py

# Terminal 4 - Worker 3
RQ_WORKER_NAME=worker-3 python worker.py
```

#### Monitoring Workers

Check queue status:

```python
from redis import Redis
from rq import Queue

redis_conn = Redis.from_url("your-redis-url")
queue = Queue("scraper", connection=redis_conn)

print(f"Jobs in queue: {len(queue)}")
print(f"Failed jobs: {queue.failed_job_registry.count}")
```

Or use RQ's built-in dashboard:

```bash
pip install rq-dashboard
rq-dashboard --redis-url your-redis-url
```

Visit `http://localhost:9181` to see the dashboard.

## Next Steps

- Swap in Playwright for rich DOM capture when simple HTTP fetches are insufficient.
- Expand the LLM prompt based on desired schema and add validation/guardrails.
- Orchestrate multiple agent steps (crawl, segment, vision, etc.).
- Add rate limiting and caching to the API layer.
