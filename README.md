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

**Scrape and Analyze Product**
```
POST /scrape
```

Request body:
```json
{
  "source_url": "https://www.leadspace.com/"
}
```

```
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

#### Interactive Documentation

Visit `http://localhost:8000/docs` for Swagger UI documentation or `http://localhost:8000/redoc` for ReDoc documentation.

## Next Steps

- Swap in Playwright for rich DOM capture when simple HTTP fetches are insufficient.
- Expand the LLM prompt based on desired schema and add validation/guardrails.
- Orchestrate multiple agent steps (crawl, segment, vision, etc.).
- Add rate limiting and caching to the API layer.
