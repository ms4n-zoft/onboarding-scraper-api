# Product Scraper Engine

Production-ready web scraping and analysis engine powered by Azure OpenAI, with async job processing, real-time event streaming, and comprehensive API.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│  API Server │────▶│    Redis    │
│  (Browser)  │◀────│  (FastAPI)  │◀────│   (Queue)   │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌─────────────┐
                                        │ RQ Workers  │
                                        │  (N nodes)  │
                                        └─────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (Upstash recommended for cloud deployment)
- Azure OpenAI resource with GPT-4 deployment

### Installation

1. **Clone and setup virtual environment**:

   ```bash
   git clone https://github.com/your-org/product-scraper-engine.git
   cd product-scraper-engine
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

   Required variables:

   - `AZURE_OPENAI_ENDPOINT`
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_DEPLOYMENT_NAME`
   - `REDIS_URL`

   See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for complete reference.

4. **Verify setup**:
   ```bash
   python tests/test_worker_setup.py
   ```

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

## Testing

### Unit and Integration Tests

```bash
# Test Redis configuration
python tests/test_redis.py

# Test event emitter
python tests/test_redis_event_emitter.py

# Test worker setup
python tests/test_worker_setup.py

# Test API endpoints
python tests/test_async_endpoint.py
python tests/test_stream_endpoint.py
python tests/test_status_result_endpoints.py

# Integration test (requires worker running)
python tests/test_integration.py
```

### Manual Testing

```bash
# Terminal 1: Start worker
python worker.py

# Terminal 2: Submit a test job
python tests/test_worker_manual.py
```

## Documentation

- **[ENVIRONMENT_VARIABLES.md](docs/ENVIRONMENT_VARIABLES.md)** - Complete environment variable reference
- **[FRONTEND_API_DOCS.md](docs/FRONTEND_API_DOCS.md)** - API documentation for frontend integration

## Project Structure

```
product-scraper-engine/
├── src/
│   ├── api.py                  # FastAPI application and endpoints
│   ├── main.py                 # CLI entry point
│   ├── dependencies.py         # Dependency injection (Redis, Queue)
│   ├── ai/
│   │   ├── analyzer.py         # Synchronous AI analyzer
│   │   └── agentic_analyzer.py # Agentic AI analyzer
│   ├── config/
│   │   ├── azure.py            # Azure OpenAI configuration
│   │   └── redis.py            # Redis connection management
│   ├── jobs/
│   │   └── scraper_task.py     # RQ worker job functions
│   ├── schemas/
│   │   ├── api.py              # API request/response models
│   │   ├── events.py           # SSE event models
│   │   └── product.py          # Product data schemas
│   ├── scraper/
│   │   ├── fetcher.py          # HTTP fetching utilities
│   │   └── parser.py           # HTML parsing utilities
│   └── utils/
│       ├── env.py              # Environment variable utilities
│       ├── event_emitter.py    # Base event emitter
│       ├── redis_event_emitter.py # Redis-backed event emitter
│       └── logging.py          # Logging configuration
├── tests/
│   ├── test_redis.py           # Redis connection tests
│   ├── test_redis_event_emitter.py # Event emitter tests
│   ├── test_rq_job.py          # Job execution tests
│   ├── test_async_endpoint.py  # Async endpoint tests
│   ├── test_stream_endpoint.py # SSE streaming tests
│   ├── test_status_result_endpoints.py # Status/result tests
│   ├── test_worker_setup.py    # Worker configuration tests
│   ├── test_worker_manual.py   # Manual worker testing
│   └── test_integration.py     # End-to-end integration test
├── worker.py                   # RQ worker entry point
├── requirements.txt            # Python dependencies
└── .env.example                # Environment variable template
```
