# Product Scraper Engine - Frontend API Documentation

## Overview

The Product Scraper Engine provides intelligent web scraping and product data extraction using AI-powered analysis. This document explains all API endpoints, their usage patterns, and integration considerations for frontend applications.

### Base URL

```
Development: http://localhost:8000
Production: [TBD]
```

### Implementation Status

- ✅ **Async Job Processing**: Production ready with RQ + Redis
- ✅ **Real-time Streaming**: SSE with reconnection support
- ✅ **Job Persistence**: 24-hour retention in Redis
- ✅ **Event Replay**: Full event history on reconnection

---

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. POST /scrape/async → returns job_id
       │ 2. GET /jobs/{id}/stream → SSE for events
       │ 3. GET /jobs/{id}/status → poll status (optional)
       │ 4. GET /jobs/{id}/result → get final result
       │
┌──────▼──────────────────┐
│  FastAPI Server         │
│  - Job management       │
│  - Event streaming      │
└────┬────────────────────┘
     │
┌────▼────┐
│  Redis  │  ← Stores jobs, events, results (24h TTL)
└────┬────┘
     │
┌────▼────────┐
│ RQ Workers  │  ← Background scraping
└─────────────┘
```

---

## API Endpoints

### 1. Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "service": "Product Scraper Engine"
}
```

**Usage:** Verify API availability before submitting jobs.

---

### 2. Submit Async Scraping Job

```http
POST /scrape/async
Content-Type: application/json
```

**Request:**

```json
{
  "source_url": "https://example.com/product"
}
```

**Response:**

```json
{
  "job_id": "abc-123-def-456",
  "status": "queued",
  "stream_url": "/jobs/abc-123-def-456/stream"
}
```

**Usage Pattern:**

1. Submit URL to create background job
2. Store `job_id` in localStorage for resume capability
3. Immediately connect to `stream_url` for real-time updates
4. Job processes in background (1-2 minutes typical)

**Error Response:**

```json
{
  "detail": "Invalid URL format"
}
```

---

### 3. Stream Job Events (SSE)

```http
GET /jobs/{job_id}/stream
```

**Response Type:** `text/event-stream` (Server-Sent Events)

**Event Types:**

| Event      | When                      | Payload Fields                      |
| ---------- | ------------------------- | ----------------------------------- |
| `start`    | Job begins processing     | `message`                           |
| `reading`  | Fetching a URL            | `message`, `url`                    |
| `update`   | Analysis progress         | `message`                           |
| `complete` | Job finished successfully | `message`, `data` (ProductSnapshot) |
| `error`    | Job failed                | `message`, `error`                  |

**Example Events:**

```javascript
// Start Event
data: {"event":"start","message":"Checking out your website"}

// Reading Event
data: {"event":"reading","url":"https://example.com/pricing","message":"Reading https://example.com/pricing"}

// Update Event
data: {"event":"update","message":"Analyzing product information..."}

// Complete Event
data: {"event":"complete","message":"All done!","data":{...ProductSnapshot...}}

// Error Event
data: {"event":"error","message":"Scraping failed","error":"HTTPError: 404"}
```

**Key Features:**

- ✅ **Event Replay**: On reconnect, all past events are replayed from Redis
- ✅ **Resumable**: Can close and reopen connection anytime
- ✅ **Real-time**: New events stream as they occur
- ✅ **Persistent**: Events stored for 24 hours

**Usage Pattern:**

1. Open SSE connection immediately after job submission
2. Listen for events and update UI progressively
3. On `complete` event, extract `data` field for final result
4. On page refresh, reconnect with same job_id to resume
5. Store job_id in localStorage until `complete` or `error`

**Reconnection Behavior:**

```
First connection:
→ Replays: [start, reading, update]
→ Streams live: [update, update, complete]

Page refresh → Second connection:
→ Replays: [start, reading, update, update, update]
→ Streams live: [complete]
```

---

### 4. Get Job Status

```http
GET /jobs/{job_id}/status
```

**Response (Queued):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "queued",
  "position_in_queue": 3,
  "created_at": "2025-01-05T10:30:00Z",
  "enqueued_at": "2025-01-05T10:30:00Z"
}
```

**Response (Started):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "started",
  "created_at": "2025-01-05T10:30:00Z",
  "started_at": "2025-01-05T10:30:15Z",
  "worker_name": "worker-1"
}
```

**Response (Finished):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "finished",
  "created_at": "2025-01-05T10:30:00Z",
  "started_at": "2025-01-05T10:30:15Z",
  "ended_at": "2025-01-05T10:32:00Z"
}
```

**Response (Failed):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "failed",
  "created_at": "2025-01-05T10:30:00Z",
  "started_at": "2025-01-05T10:30:15Z",
  "ended_at": "2025-01-05T10:31:00Z",
  "error": "HTTPError: 404 Not Found"
}
```

**Status Values:**

- `queued` - Waiting for worker
- `started` - Currently processing
- `finished` - Completed successfully
- `failed` - Encountered error

**Usage Pattern:**

- **Primary**: Use SSE streaming for real-time updates (recommended)
- **Alternative**: Poll this endpoint every 2-5 seconds if SSE not available
- **Fallback**: Check status after page refresh before reconnecting to SSE
- **Debugging**: Verify job exists and current state

**When to Use Polling:**

- Client doesn't support SSE (rare)
- Network firewall blocks SSE
- Simple status display without event details

---

### 5. Get Job Result

```http
GET /jobs/{job_id}/result
```

**Response (Success):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "finished",
  "result": {
    "product_name": "Example Product",
    "company_name": "Example Inc",
    "description": "Product description...",
    "pricing_plans": [...],
    // ... full ProductSnapshot
  }
}
```

**Response (In Progress):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "started",
  "result": null
}
```

**Response (Failed):**

```json
{
  "job_id": "abc-123-def-456",
  "status": "failed",
  "error": "HTTPError: 404 Not Found",
  "result": null
}
```

**Response (Not Found):**

```json
{
  "detail": "Job not found or expired"
}
```

**Usage Pattern:**

1. **After SSE complete event**: Extract result from event data (faster)
2. **On page refresh**: Check if job finished, then fetch result
3. **Result retrieval**: Use this endpoint to get final data without SSE
4. **Job history**: Access past results within 24-hour window

---

### 6. Legacy Real-Time Endpoint (Optional)

```http
POST /scrape/stream
Content-Type: application/json
```

**Request:**

```json
{
  "source_url": "https://example.com/product"
}
```

**Response:** Server-Sent Events (same format as job stream)

**Differences from Async:**

- ❌ No job_id (cannot resume)
- ❌ No reconnection support
- ❌ No result persistence
- ✅ Slightly faster (no Redis overhead)
- ✅ Simpler integration (one request)

**When to Use:**

- Quick one-off scrapes
- User will wait on same page
- No need for job history
- Prototyping/testing

---

## Integration Patterns

### Recommended Flow

**1. Initial Job Submission**

```
User enters URL
  ↓
POST /scrape/async
  ↓
Receive job_id
  ↓
localStorage.setItem('currentJobId', job_id)
  ↓
Connect to /jobs/{job_id}/stream (SSE)
  ↓
Show progress as events arrive
```

**2. Page Refresh (Resume)**

```
Page loads
  ↓
Check localStorage for currentJobId
  ↓
If exists:
  ├─ GET /jobs/{job_id}/status
  ├─ If finished/failed: GET /jobs/{job_id}/result
  └─ If queued/started: Connect to /jobs/{job_id}/stream
  ↓
Display result or resume progress
```

**3. Job Completion**

```
Receive 'complete' or 'error' event
  ↓
localStorage.removeItem('currentJobId')
  ↓
Close SSE connection
  ↓
Display final result
```

### LocalStorage Management

**Store on Job Start:**

```javascript
localStorage.setItem("currentJobId", job_id);
localStorage.setItem("jobStartTime", Date.now());
localStorage.setItem("jobUrl", source_url); // Optional: for display
```

**Check on Page Load:**

```javascript
const jobId = localStorage.getItem("currentJobId");
const startTime = localStorage.getItem("jobStartTime");

if (jobId && startTime) {
  const elapsed = Date.now() - startTime;

  if (elapsed > 24 * 60 * 60 * 1000) {
    // Job expired (>24 hours)
    localStorage.removeItem("currentJobId");
  } else {
    // Job might still be active, check status
    resumeJob(jobId);
  }
}
```

**Clear on Completion:**

```javascript
// On 'complete' or 'error' event
localStorage.removeItem("currentJobId");
localStorage.removeItem("jobStartTime");
localStorage.removeItem("jobUrl");
```

### Polling Strategy (Alternative to SSE)

**When to Poll:**

- SSE connection repeatedly fails
- Client environment blocks streaming
- Simple status display needed

**Polling Implementation:**

```
1. Submit job via POST /scrape/async
2. Start polling loop:
   - GET /jobs/{job_id}/status every 2-5 seconds
   - Stop when status is 'finished' or 'failed'
3. When complete:
   - GET /jobs/{job_id}/result to retrieve data
```

**Polling Best Practices:**

- Start with 2s interval, increase to 5s after 30s
- Maximum 5 minutes total polling time
- Stop on 'finished', 'failed', or timeout
- Show "Taking longer than expected" after 2 minutes

### Error Handling

**Network Errors:**

- Retry SSE connection up to 3 times with exponential backoff
- Fall back to polling if SSE repeatedly fails
- Show connection status to user

**Job Errors:**

- Display error message from 'error' event or status endpoint
- Offer "Try Again" button
- Log error details for debugging

**Timeout Scenarios:**

- Jobs timeout after 10 minutes (server-side)
- Show progress indicator for expected 1-2 minute duration
- Warn user if job exceeds 3 minutes

---

## ProductSnapshot Schema

### Complete Structure

```json
{
  "product_name": "string | null",
  "company_name": "string | null",
  "description": "string | null",
  "tagline": "string | null",
  "website_url": "string | null",
  "logo_url": "string | null",
  "headquarters_location": "string | null",
  "founding_year": "number | null",
  "company_size": "string | null",

  "categories": ["string"],
  "target_audiences": ["string"],
  "key_features": ["string"],
  "integrations": ["string"],
  "supported_platforms": ["string"],
  "languages_supported": ["string"],

  "pricing_plans": [
    {
      "plan_name": "string",
      "price_amount": "number | null",
      "price_currency": "string | null",
      "billing_period": "string | null",
      "features_included": ["string"]
    }
  ],

  "social_media": {
    "twitter": "string | null",
    "linkedin": "string | null",
    "facebook": "string | null",
    "github": "string | null"
  },

  "reviews": [
    {
      "platform": "string",
      "rating": "number | null",
      "review_count": "number | null",
      "review_url": "string | null"
    }
  ],

  "security_compliance": ["string"],
  "api_available": "boolean | null",
  "free_trial_available": "boolean | null",
  "support_channels": ["string"]
}
```

**Field Notes:**

- All fields can be `null` if not found
- Arrays are empty `[]` if no data found
- Use null-checking when displaying values
- `price_amount` is a number (e.g., 99.00)
- `billing_period`: "monthly", "annually", "one-time", etc.

---

## Common Scenarios

### Scenario 1: First-Time User

```
User visits page
  ↓
User enters URL
  ↓
Submit job, store job_id
  ↓
Connect to SSE stream
  ↓
Show live progress
  ↓
Display final result
```

### Scenario 2: User Refreshes During Scraping

```
Page reloads
  ↓
Find job_id in localStorage
  ↓
Check job status
  ↓
Reconnect to SSE (replay + live events)
  ↓
Continue showing progress
```

### Scenario 3: User Returns After 10 Minutes

```
Page loads
  ↓
Find job_id in localStorage
  ↓
Check job status → "finished"
  ↓
Fetch result from /jobs/{id}/result
  ↓
Display cached result
  ↓
Clear localStorage
```

### Scenario 4: SSE Connection Fails

```
SSE connection error
  ↓
Retry connection (3 attempts)
  ↓
If still failing:
  ├─ Fall back to polling
  └─ GET /jobs/{id}/status every 3s
  ↓
When finished, fetch result
```

### Scenario 5: Job Fails

```
Receive 'error' event
  ↓
Display error message to user
  ↓
Clear localStorage
  ↓
Offer "Try Again" button
```

---

## Performance Considerations

### Expected Timing

- **Job submission**: <100ms
- **Queue wait**: 0-30s (depends on load)
- **Scraping duration**: 1-2 minutes typical
- **Total time**: 1-3 minutes end-to-end

### Resource Usage

- **SSE connection**: ~1KB/minute data transfer
- **Polling**: ~0.5KB per request
- **Result size**: 5-50KB depending on product

### Optimization Tips

1. **Reuse job results**: Cache in localStorage for 24 hours
2. **Debounce URL input**: Wait 500ms before submission
3. **Show estimated time**: "Usually takes 1-2 minutes"
4. **Progressive display**: Show data as events arrive
5. **Lazy load**: Only fetch full result when user requests

---

## Error Codes & Troubleshooting

### HTTP Status Codes

| Code | Meaning             | Solution                              |
| ---- | ------------------- | ------------------------------------- |
| 200  | Success             | -                                     |
| 400  | Invalid URL         | Validate URL format before submission |
| 404  | Job not found       | Job expired or invalid job_id         |
| 422  | Validation error    | Check request body matches schema     |
| 500  | Server error        | Retry request, report if persists     |
| 503  | Service unavailable | Workers offline, retry later          |

### Common Errors

**"Job not found or expired"**

- Job_id is >24 hours old
- Job_id is invalid
- Solution: Submit new job

**"Invalid URL format"**

- URL missing protocol (http/https)
- URL is malformed
- Solution: Validate URL client-side first

**SSE connection drops**

- Network interruption
- Server restart
- Solution: Reconnect automatically with same job_id

**Job stuck in "queued"**

- No workers available
- High queue load
- Solution: Show "Queue position" from status endpoint

**Job timeout**

- Website took >10 minutes to scrape
- Website blocking requests
- Solution: Show timeout message, offer retry

---

## Security Considerations

### URL Validation

- Validate URL format client-side before submission
- Warn users about scraping third-party sites
- Consider URL whitelist for production

### Rate Limiting

- Implement client-side debouncing (500ms)
- Track jobs per user/session
- Respect server rate limits (if implemented)

### Data Privacy

- Job results deleted after 24 hours
- No job history tracking (yet)
- Consider implementing user authentication for production

---

## Testing & Development

### Test Endpoints

**Quick health check:**

```bash
curl http://localhost:8000/health
```

**Submit test job:**

```bash
curl -X POST http://localhost:8000/scrape/async \
  -H "Content-Type: application/json" \
  -d '{"source_url":"https://example.com"}'
```

**Check job status:**

```bash
curl http://localhost:8000/jobs/{job_id}/status
```

**Stream events (terminal):**

```bash
curl -N http://localhost:8000/jobs/{job_id}/stream
```

### Development Mode

**CORS:** Enabled for `http://localhost:3000` and `http://localhost:5173` (Vite default)

**Logs:** Check worker logs in `logs/worker_*.log` for debugging

**Queue monitoring:** Install RQ Dashboard:

```bash
pip install rq-dashboard
rq-dashboard --redis-url $REDIS_URL
```

---

## Roadmap & Future Features

### Planned Enhancements

- 🔄 Webhook notifications on job completion
- 📊 Job history and analytics
- 🔐 User authentication and job ownership
- ⚡ Job priority queues
- 📅 Scheduled recurring scrapes
- 🎯 Custom extraction schemas
- 🔄 Automatic retry on failure

### Breaking Changes (None Planned)

All current endpoints will remain stable. New features will be additive.

---

## Support

**Documentation:**

- API Docs: This file
- Setup Guide: `README.md`
- Environment Variables: `ENVIRONMENT_VARIABLES.md`
- Deployment Guide: `DEPLOYMENT.md`

**Issues:**

- Backend issues: Check worker logs
- Connection issues: Verify Redis and worker status
- API questions: Contact backend team

---

## Quick Reference

### Essential Endpoints

```
POST /scrape/async          → Submit job
GET /jobs/{id}/stream       → Stream events (SSE)
GET /jobs/{id}/status       → Check status
GET /jobs/{id}/result       → Get final result
```

### localStorage Keys

```
currentJobId    → Active job ID
jobStartTime    → Job submission timestamp
jobUrl          → Original URL (optional)
```

### Job Lifecycle

```
queued → started → finished (with result)
                ↘ failed (with error)
```

### Event Flow

```
start → reading → update → update → complete
                                 ↘ error
```
