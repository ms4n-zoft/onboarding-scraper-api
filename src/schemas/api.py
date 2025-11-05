"""Request and response models for API endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field
from .product import ProductSnapshot


class ScrapeRequest(BaseModel):
    """Request model for scraping operations."""
    source_url: str = Field(
        ..., 
        description="The URL of the product page to scrape",
        example="https://example.com/product"
    )


class ScrapeResponse(BaseModel):
    """Response model for synchronous scrape operations."""
    success: bool = Field(description="Whether the operation was successful")
    data: ProductSnapshot = Field(description="Extracted product information")
    error: str | None = Field(default=None, description="Error message if operation failed")


class AsyncScrapeResponse(BaseModel):
    """Response model for async scrape job submission."""
    job_id: str = Field(description="Unique job identifier for tracking")
    status: str = Field(description="Initial job status (queued)")
    stream_url: str = Field(description="SSE endpoint URL for this job")


class JobStatus(BaseModel):
    """Response model for job status queries."""
    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Current job status: queued, started, finished, failed")
    enqueued_at: str | None = Field(default=None, description="ISO timestamp when job was enqueued")
    started_at: str | None = Field(default=None, description="ISO timestamp when job started")
    ended_at: str | None = Field(default=None, description="ISO timestamp when job ended")


class JobStatusResponse(BaseModel):
    """Extended response model for job status endpoint."""
    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Current job status: queued, started, finished, failed, deferred")
    enqueued_at: str | None = Field(default=None, description="ISO timestamp when job was enqueued")
    started_at: str | None = Field(default=None, description="ISO timestamp when job started")
    ended_at: str | None = Field(default=None, description="ISO timestamp when job ended")
    position: int | None = Field(default=None, description="Position in queue if job is queued")
    exc_info: str | None = Field(default=None, description="Exception information if job failed")


class JobResultResponse(BaseModel):
    """Response model for job result retrieval."""
    job_id: str = Field(description="Unique job identifier")
    status: str = Field(description="Final job status")
    result: ProductSnapshot | None = Field(default=None, description="Extracted product information")
    error: str | None = Field(default=None, description="Error message if job failed")
