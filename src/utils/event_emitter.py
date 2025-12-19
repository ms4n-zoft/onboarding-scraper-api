"""Event emitter for streaming scraper updates via SSE."""
from __future__ import annotations

import json
from typing import Callable, Any
from loguru import logger

from ..schemas.events import (
    StartEvent,
    ReadingEvent,
    UpdateEvent,
    CompleteEvent,
    ErrorEvent,
)


class EventEmitter:
    """Emits user-friendly events during scraping for SSE streaming."""

    def __init__(self, callback: Callable[[Any], None] | None = None):
        """Initialize event emitter with optional callback.

        Args:
            callback: Function to call with each event. If None, no events are emitted.
        """
        self.callback = callback

    def emit_start(self) -> None:
        """Emit a start event."""
        if self.callback:
            self.callback(StartEvent(message="Checking out your website"))

    def emit_update(self, message: str) -> None:
        """Emit a progress update event.

        Args:
            message: Progress message
        """
        if self.callback:
            self.callback(UpdateEvent(message=message))

    def emit_reading(self, url: str) -> None:
        """Emit a reading page event.

        Args:
            url: URL being read
        """
        if self.callback:
            self.callback(ReadingEvent(url=url, message=f"Reading {url}"))

    def emit_complete(self, message: str = "All done! Your product information is ready", data: dict | None = None) -> None:
        """Emit a completion event.

        Args:
            message: Completion message
            data: Optional final product data (ProductSnapshot as dict)
        """
        if self.callback:
            self.callback(CompleteEvent(message=message, data=data or {}))

    def emit_error(self, message: str, error: str) -> None:
        """Emit an error event.

        Args:
            message: User-friendly error message
            error: Detailed error information
        """
        if self.callback:
            self.callback(ErrorEvent(message=message, error=error))
