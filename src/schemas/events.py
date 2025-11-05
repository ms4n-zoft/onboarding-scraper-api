"""Server-Sent Events schemas for streaming scraper updates."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events sent via SSE."""
    START = "start"
    READING = "reading"
    UPDATE = "update"
    COMPLETE = "complete"
    ERROR = "error"


class StartEvent(BaseModel):
    """Event sent when scraping starts."""
    event: EventType = Field(default=EventType.START)
    message: str = Field(description="Welcome message for the user")


class ReadingEvent(BaseModel):
    """Event sent when reading a page."""
    event: EventType = Field(default=EventType.READING)
    url: str = Field(description="URL being read")
    message: str = Field(description="Friendly message about reading the page")


class UpdateEvent(BaseModel):
    """Event for general progress updates."""
    event: EventType = Field(default=EventType.UPDATE)
    message: str = Field(description="Progress message")


class CompleteEvent(BaseModel):
    """Event sent when scraping is complete."""
    event: EventType = Field(default=EventType.COMPLETE)
    message: str = Field(default="Scraping complete")
    data: dict = Field(description="The final ProductSnapshot as dict")


class ErrorEvent(BaseModel):
    """Event sent when an error occurs."""
    event: EventType = Field(default=EventType.ERROR)
    message: str = Field(description="Error message")
    error: str = Field(description="Detailed error information")
