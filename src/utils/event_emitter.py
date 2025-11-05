"""Event emitter for streaming scraper updates via SSE."""
from __future__ import annotations

import json
from typing import Callable, Any
from loguru import logger

from ..schemas.events import (
    ToolCallEvent,
    ToolResultEvent,
    ProgressEvent,
)


class EventEmitter:
    """Emits events during scraping for SSE streaming."""

    def __init__(self, callback: Callable[[Any], None] | None = None):
        """Initialize event emitter with optional callback.

        Args:
            callback: Function to call with each event. If None, no events are emitted.
        """
        self.callback = callback

    def emit_progress(self, message: str, iteration: int | None = None) -> None:
        """Emit a progress event."""
        if self.callback:
            self.callback(ProgressEvent(message=message, iteration=iteration))

    def emit_tool_call(self, tool_name: str, arguments: str) -> None:
        """Emit a tool call event.

        Args:
            tool_name: Name of the tool being called
            arguments: JSON string of tool arguments
        """
        if not self.callback:
            return

        # Special handling for fetch_page_text to extract URL
        if tool_name == "fetch_page_text":
            try:
                args = json.loads(arguments)
                url = args.get("url", "unknown")
                self.callback(ToolCallEvent(
                    tool_name=tool_name,
                    url=url,
                    message=f"Reading page: {url}"
                ))
            except Exception as e:
                logger.warning(f"Failed to parse tool arguments: {e}")
                self.callback(ToolCallEvent(
                    tool_name=tool_name,
                    url=None,
                    message=f"Calling tool: {tool_name}"
                ))
        else:
            self.callback(ToolCallEvent(
                tool_name=tool_name,
                url=None,
                message=f"Calling tool: {tool_name}"
            ))

    def emit_tool_result(self, tool_call_id: str, success: bool) -> None:
        """Emit a tool result event.

        Args:
            tool_call_id: ID of the tool call that completed
            success: Whether the tool call succeeded
        """
        if self.callback:
            self.callback(ToolResultEvent(
                tool_name=tool_call_id,
                success=success,
                message=f"Completed: {tool_call_id}" if success else f"Failed: {tool_call_id}"
            ))
