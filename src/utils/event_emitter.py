"""Event emitter for streaming scraper updates via SSE."""
from __future__ import annotations

import json
from typing import Callable, Any
from loguru import logger

from ..schemas.events import (
    StartEvent,
    ReadingEvent,
    UpdateEvent,
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
