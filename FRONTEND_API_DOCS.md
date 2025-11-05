# Product Scraper Engine - Frontend API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Phase 1: Current Implementation (SSE Streaming)](#phase-1-current-implementation)
3. [Phase 2: Planned Implementation (RQ + Redis)](#phase-2-planned-implementation)
4. [Migration Guide](#migration-guide)

---

## Overview

The Product Scraper Engine provides intelligent web scraping and product data extraction using AI-powered analysis. This document outlines the API endpoints and integration patterns for frontend applications.

### Base URL
```
Development: http://localhost:8000
Production: [TBD]
```

### Key Features
- Real-time progress updates via Server-Sent Events (SSE)
- Structured product data extraction
- Event trail for debugging and transparency
- User-friendly progress messages

---

## Phase 1: Current Implementation

**Status**: ✅ Deployed and Available
**Use Case**: Real-time scraping with live feedback

### Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ POST /scrape/stream
       │ (SSE Connection - stays open)
       │
┌──────▼──────────────┐
│  FastAPI Server     │
│  - Runs scraping    │
│  - Streams events   │
└─────────────────────┘
```

### Endpoints

#### 1. Health Check
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

---

#### 2. Scrape with Real-Time Streaming (SSE)
```http
POST /scrape/stream
Content-Type: application/json
```

**Request Body:**
```json
{
  "source_url": "https://example.com/product"
}
```

**Response:** Server-Sent Events (text/event-stream)

**Event Types:**

| Event Type | Description | Example |
|------------|-------------|---------|
| `start` | Scraping initiated | Checking out your website |
| `reading` | Fetching a specific page | Reading https://example.com/pricing |
| `update` | Analysis progress | Analyzing... |
| `complete` | Scraping finished with result | All done! Your product information is ready |
| `error` | Something went wrong | Scraping failed |

**Event Structure:**

```javascript
// Start Event
{
  "event": "start",
  "message": "Checking out your website"
}

// Reading Event (includes URL)
{
  "event": "reading",
  "url": "https://example.com/pricing",
  "message": "Reading https://example.com/pricing"
}

// Update Event
{
  "event": "update",
  "message": "Analyzing..."
}

// Complete Event (includes full result)
{
  "event": "complete",
  "message": "All done! Your product information is ready",
  "data": {
    // Full ProductSnapshot object
    "product_name": "Example Product",
    "company_name": "Example Inc",
    "description": "...",
    "pricing_plans": [...],
    // ... more fields
  }
}

// Error Event
{
  "event": "error",
  "message": "Scraping failed",
  "error": "Detailed error message"
}
```

---

### Frontend Integration Examples

#### JavaScript (Fetch API)

```javascript
async function startScraping(url) {
  const response = await fetch('http://localhost:8000/scrape/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ source_url: url })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    lines.forEach(line => {
      if (line.startsWith('data: ')) {
        const eventData = JSON.parse(line.substring(6));
        handleEvent(eventData);
      }
    });
  }
}

function handleEvent(event) {
  switch(event.event) {
    case 'start':
      console.log('Started:', event.message);
      break;
    case 'reading':
      console.log('Reading:', event.url);
      updateProgress(`Reading ${event.url}`);
      break;
    case 'update':
      console.log('Update:', event.message);
      break;
    case 'complete':
      console.log('Complete!');
      displayResult(event.data);
      break;
    case 'error':
      console.error('Error:', event.error);
      showError(event.message);
      break;
  }
}
```

#### React Example

```jsx
import { useState, useEffect } from 'react';

function ProductScraper() {
  const [url, setUrl] = useState('');
  const [events, setEvents] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const startScraping = async () => {
    setLoading(true);
    setEvents([]);
    setResult(null);

    try {
      const response = await fetch('http://localhost:8000/scrape/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_url: url })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            const eventData = JSON.parse(line.substring(6));

            setEvents(prev => [...prev, eventData]);

            if (eventData.event === 'complete') {
              setResult(eventData.data);
              setLoading(false);
            } else if (eventData.event === 'error') {
              setLoading(false);
            }
          }
        });
      }
    } catch (error) {
      console.error('Error:', error);
      setLoading(false);
    }
  };

  return (
    <div>
      <input
        value={url}
        onChange={e => setUrl(e.target.value)}
        placeholder="Enter product URL"
      />
      <button onClick={startScraping} disabled={loading}>
        {loading ? 'Scraping...' : 'Start Scraping'}
      </button>

      <div className="events">
        {events.map((event, i) => (
          <div key={i} className={`event-${event.event}`}>
            {event.message}
            {event.url && <small>{event.url}</small>}
          </div>
        ))}
      </div>

      {result && (
        <pre>{JSON.stringify(result, null, 2)}</pre>
      )}
    </div>
  );
}
```

---

### Current Limitations

⚠️ **Important to Know:**

1. **No Reconnection**: If the user refreshes the page during scraping, the connection is lost and progress cannot be recovered.
2. **No Job Persistence**: Results are only available during the active connection.
3. **Blocking Connection**: The HTTP connection remains open for the entire duration (1-2 minutes).
4. **No Job History**: Cannot retrieve past scraping results.
5. **Single User Focus**: Best suited for one-off scraping where user waits for completion.

**Recommendation**: Inform users to **keep the page open** until scraping completes.

---

## Phase 2: Planned Implementation (RQ + Redis)

**Status**: 🚧 In Development
**ETA**: [TBD]
**Use Case**: Scalable, resumable scraping with job management

### Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ 1. POST /scrape/async → returns job_id
       │ 2. GET /jobs/{id}/stream → SSE for events
       │ 3. GET /jobs/{id}/status → poll status
       │ 4. GET /jobs/{id}/result → get final result
       │
┌──────▼──────────────────┐
│  FastAPI Server         │
│  - Job management       │
│  - Event streaming      │
└────┬────────────────────┘
     │
┌────▼────┐
│  Redis  │  ← Stores jobs, events, results
└────┬────┘
     │
┌────▼────────┐
│ RQ Workers  │  ← Background scraping
└─────────────┘
```

### New Endpoints

#### 1. Submit Async Scraping Job
```http
POST /scrape/async
Content-Type: application/json
```

**Request Body:**
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
  "created_at": "2025-01-05T10:30:00Z"
}
```

---

#### 2. Stream Job Events (SSE with Reconnection)
```http
GET /jobs/{job_id}/stream
```

**Response:** Server-Sent Events (same format as Phase 1)

**Key Difference**:
- ✅ **Reconnection Support**: On reconnect, all past events are replayed from Redis
- ✅ **Resumable**: Can close and reopen the stream anytime

**Example:**
```javascript
// First connection - streams all events
const eventSource = new EventSource('/jobs/abc-123/stream');

// User refreshes page...

// Second connection - replays ALL past events, then continues
const eventSource = new EventSource('/jobs/abc-123/stream');
```

---

#### 3. Get Job Status
```http
GET /jobs/{job_id}/status
```

**Response:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "started",  // queued | started | finished | failed
  "created_at": "2025-01-05T10:30:00Z",
  "progress": {
    "current_step": "Reading https://example.com/pricing",
    "events_count": 5
  }
}
```

---

#### 4. Get Job Result
```http
GET /jobs/{job_id}/result
```

**Response (if complete):**
```json
{
  "job_id": "abc-123-def-456",
  "status": "finished",
  "data": {
    // Full ProductSnapshot object
    "product_name": "Example Product",
    // ... all fields
  }
}
```

**Response (if not complete):**
```json
{
  "job_id": "abc-123-def-456",
  "status": "started",
  "message": "Job is still in progress"
}
```

---

#### 5. Legacy SSE Endpoint (Kept for Compatibility)
```http
POST /scrape/stream
```

**Note**: This endpoint will remain available for users who want immediate, real-time scraping without job management.

---

### Frontend Integration Examples (Phase 2)

#### Async Job with Reconnection Support

```javascript
class ScraperClient {
  constructor() {
    this.jobId = localStorage.getItem('currentJobId');
  }

  // Submit new job
  async startJob(url) {
    const response = await fetch('/scrape/async', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_url: url })
    });

    const data = await response.json();
    this.jobId = data.job_id;
    localStorage.setItem('currentJobId', this.jobId);

    return this.jobId;
  }

  // Connect to job event stream (supports reconnection)
  connectToJob(jobId, onEvent) {
    const eventSource = new EventSource(`/jobs/${jobId}/stream`);

    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      onEvent(event);

      // Clean up on completion
      if (event.event === 'complete' || event.event === 'error') {
        localStorage.removeItem('currentJobId');
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      eventSource.close();
    };

    return eventSource;
  }

  // Poll for status (alternative to SSE)
  async getStatus(jobId) {
    const response = await fetch(`/jobs/${jobId}/status`);
    return response.json();
  }

  // Get final result
  async getResult(jobId) {
    const response = await fetch(`/jobs/${jobId}/result`);
    return response.json();
  }

  // Resume existing job on page load
  resumeExistingJob(onEvent) {
    if (this.jobId) {
      return this.connectToJob(this.jobId, onEvent);
    }
    return null;
  }
}
```

#### React Hook for Job Management

```jsx
import { useState, useEffect } from 'react';

function useScraperJob() {
  const [jobId, setJobId] = useState(null);
  const [events, setEvents] = useState([]);
  const [result, setResult] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | queued | started | finished | failed

  // Resume job on mount
  useEffect(() => {
    const savedJobId = localStorage.getItem('currentJobId');
    if (savedJobId) {
      setJobId(savedJobId);
      connectToJobStream(savedJobId);
    }
  }, []);

  const startJob = async (url) => {
    const response = await fetch('/scrape/async', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_url: url })
    });

    const data = await response.json();
    setJobId(data.job_id);
    setStatus('queued');
    localStorage.setItem('currentJobId', data.job_id);

    connectToJobStream(data.job_id);
  };

  const connectToJobStream = (id) => {
    const eventSource = new EventSource(`/jobs/${id}/stream`);

    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      setEvents(prev => [...prev, event]);

      if (event.event === 'start') setStatus('started');

      if (event.event === 'complete') {
        setResult(event.data);
        setStatus('finished');
        localStorage.removeItem('currentJobId');
        eventSource.close();
      }

      if (event.event === 'error') {
        setStatus('failed');
        localStorage.removeItem('currentJobId');
        eventSource.close();
      }
    };

    return () => eventSource.close();
  };

  return {
    jobId,
    status,
    events,
    result,
    startJob
  };
}

// Usage
function App() {
  const { jobId, status, events, result, startJob } = useScraperJob();

  return (
    <div>
      {jobId && <p>Job ID: {jobId}</p>}
      <p>Status: {status}</p>

      <button onClick={() => startJob('https://example.com')}>
        Start Scraping
      </button>

      <div>
        {events.map((event, i) => (
          <div key={i}>{event.message}</div>
        ))}
      </div>

      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  );
}
```

---

### Phase 2 Benefits

✅ **Reconnection Support**: Users can refresh and resume watching job progress
✅ **Job Persistence**: Results stored for 24 hours
✅ **Scalable**: Multiple workers process jobs in background
✅ **Job History**: Can retrieve past results
✅ **Shareable**: Job URLs can be shared with team members
✅ **Resilient**: Jobs survive server restarts (in Redis)
✅ **Flexible**: Choose between real-time SSE or polling

---

## Migration Guide

### For Frontend Developers

**Phase 1 → Phase 2 Migration:**

1. **Continue using `/scrape/stream` for quick, one-off scrapes** (still supported)
2. **Switch to `/scrape/async` for production features** that need:
   - Reconnection support
   - Job history
   - Result persistence

### Recommended Approach

Offer **both modes** in your UI:

```jsx
function ScraperPage() {
  const [mode, setMode] = useState('async'); // 'realtime' or 'async'

  return (
    <div>
      <select value={mode} onChange={e => setMode(e.target.value)}>
        <option value="realtime">Real-time (Quick)</option>
        <option value="async">Background Job (Resumable)</option>
      </select>

      {mode === 'realtime' ? (
        <RealtimeScraper />  // Uses /scrape/stream
      ) : (
        <AsyncJobScraper />  // Uses /scrape/async
      )}
    </div>
  );
}
```

---

## Product Schema

### ProductSnapshot Structure

```typescript
interface ProductSnapshot {
  product_name: string | null;
  company_name: string | null;
  description: string | null;
  tagline: string | null;
  website_url: string | null;
  logo_url: string | null;
  headquarters_location: string | null;
  founding_year: number | null;
  company_size: string | null;

  categories: string[];
  target_audiences: string[];
  key_features: string[];
  integrations: string[];
  supported_platforms: string[];
  languages_supported: string[];

  pricing_plans: PricingPlan[];
  social_media: SocialMedia | null;
  reviews: Review[];

  security_compliance: string[];
  api_available: boolean | null;
  free_trial_available: boolean | null;
  support_channels: string[];
}

interface PricingPlan {
  plan_name: string;
  price_amount: number | null;
  price_currency: string | null;
  billing_period: string | null;
  features_included: string[];
}

interface SocialMedia {
  twitter: string | null;
  linkedin: string | null;
  facebook: string | null;
  github: string | null;
}

interface Review {
  platform: string;
  rating: number | null;
  review_count: number | null;
  review_url: string | null;
}
```

---

## Error Handling

### Common Error Scenarios

| Error | Cause | Solution |
|-------|-------|----------|
| Connection timeout | Page takes too long | Increase client timeout to 3+ minutes |
| Invalid URL | Malformed URL | Validate URL before submission |
| 500 Internal Error | Scraping failed | Check error event message for details |
| Job not found (Phase 2) | Invalid job_id | Verify job_id is correct |
| Job expired (Phase 2) | Job older than 24hrs | Submit new scraping job |

### Error Response Format

```json
{
  "event": "error",
  "message": "Scraping failed",
  "error": "HTTPError: 404 Not Found"
}
```

---

## Best Practices

### Phase 1 (Current)
- ✅ Show loading spinner while scraping
- ✅ Display real-time events to user
- ✅ Warn users not to refresh during scraping
- ✅ Handle connection errors gracefully
- ✅ Set reasonable timeout (3 minutes)

### Phase 2 (Upcoming)
- ✅ Store `job_id` in localStorage
- ✅ Reconnect to job on page load
- ✅ Show "Resume scraping" option if job found
- ✅ Clear localStorage when job completes
- ✅ Allow users to share job URLs
- ✅ Implement retry logic for failed connections

---

## Support

For questions or issues:
- Technical Issues: [GitHub Issues](your-repo/issues)
- API Questions: Contact backend team
- Feature Requests: [Product Board](your-board)

---

## Changelog

### v1.0.0 - Phase 1 (Current)
- ✅ Real-time SSE streaming
- ✅ Event-based progress updates
- ✅ Complete product data extraction

### v2.0.0 - Phase 2 (Planned)
- 🚧 Job queue with RQ
- 🚧 Redis persistence
- 🚧 Reconnection support
- 🚧 24-hour result retention
- 🚧 Job status polling
