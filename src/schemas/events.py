"""Server-Sent Events schemas for streaming scraper updates."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events sent via SSE."""
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    COMPLETE = "complete"
    ERROR = "error"


class ToolCallEvent(BaseModel):
    """Event sent when a tool is about to be called."""
    event: EventType = Field(default=EventType.TOOL_CALL)
    tool_name: str = Field(description="Name of the tool being called")
    url: str | None = Field(default=None, description="URL being fetched (for fetch_page_text)")
    message: str = Field(description="Human-readable message for UI display")


class ToolResultEvent(BaseModel):
    """Event sent when a tool call completes."""
    event: EventType = Field(default=EventType.TOOL_RESULT)
    tool_name: str = Field(description="Name of the tool that completed")
    success: bool = Field(description="Whether the tool call succeeded")
    message: str = Field(description="Human-readable result message")


class ProgressEvent(BaseModel):
    """Event for general progress updates."""
    event: EventType = Field(default=EventType.PROGRESS)
    message: str = Field(description="Progress message")
    iteration: int | None = Field(default=None, description="Current iteration number")


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
