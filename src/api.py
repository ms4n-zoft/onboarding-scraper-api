"""FastAPI application for product scraping and analysis."""
from __future__ import annotations

import time
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Request
from loguru import logger

from .main import scrape_and_analyze
from .schemas.product import ProductSnapshot

app = FastAPI(
    title="Product Scraper Engine",
    description="API for scraping and analyzing product information from URLs",
    version="1.0.0",
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


@app.get("/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "Product Scraper Engine"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
