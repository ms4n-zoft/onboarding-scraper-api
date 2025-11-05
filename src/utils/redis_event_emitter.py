"""Redis-backed event emitter for job event persistence."""
from __future__ import annotations

import json
from typing import Callable, Any
from redis import Redis
from loguru import logger

from .event_emitter import EventEmitter
from ..schemas.events import StartEvent, ReadingEvent, UpdateEvent, CompleteEvent, ErrorEvent


class RedisEventEmitter(EventEmitter):
    """Event emitter that persists events to Redis for job reconnection.
    
    Extends the base EventEmitter to store events in Redis while maintaining
    SSE callback support for real-time streaming. This enables job reconnection
    and event replay when clients reconnect.
    """

    def __init__(
        self,
        job_id: str,
        redis_client: Redis,
        callback: Callable[[Any], None] | None = None
    ):
        """Initialize Redis event emitter.

        Args:
            job_id: Unique job identifier
            redis_client: Redis connection instance
            callback: Optional callback for real-time SSE (called immediately on emit)
            
        Raises:
            ValueError: If job_id is empty
        """
        if not job_id:
            raise ValueError("job_id cannot be empty")
            
        super().__init__(callback)
        self.job_id = job_id
        self.redis = redis_client
        self.events_key = f"job:{job_id}:events"
        self.event_count = 0

    def _persist_event(self, event: Any) -> None:
        """Persist event to Redis list with expiration.

        Args:
            event: Pydantic event model instance
            
        Raises:
            Exception: Logged but not raised - persistence failures shouldn't stop scraping
        """
        try:
            event_json = event.model_dump_json()
            self.redis.rpush(self.events_key, event_json)
            # Set expiration to 24 hours (86400 seconds)
            self.redis.expire(self.events_key, 86400)
            self.event_count += 1
            logger.debug(f"Persisted event #{self.event_count} to Redis for job {self.job_id}")
        except Exception as e:
            logger.error(f"Failed to persist event to Redis: {e}", exc_info=True)

    def emit_start(self) -> None:
        """Emit and persist start event."""
        event = StartEvent(message="Checking out your website")
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_update(self, message: str) -> None:
        """Emit and persist update event.
        
        Args:
            message: Progress update message
        """
        event = UpdateEvent(message=message)
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_reading(self, url: str) -> None:
        """Emit and persist reading event.
        
        Args:
            url: URL being read
        """
        event = ReadingEvent(url=url, message=f"Reading {url}")
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_complete(self, message: str = "All done! Your product information is ready", data: dict | None = None) -> None:
        """Emit and persist completion event.
        
        Args:
            message: Completion message
            data: The final product data (ProductSnapshot as dict)
        """
        event = CompleteEvent(
            message=message,
            data=data or {}
        )
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_error(self, message: str, error: str) -> None:
        """Emit and persist error event.
        
        Args:
            message: User-friendly error message
            error: Detailed error information
        """
        event = ErrorEvent(message=message, error=error)
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def emit_event(self, event: Any) -> None:
        """Generic event emitter for callback compatibility.
        
        Persists any event object that has a model_dump_json() method.
        Useful for flexibility when handling different event types.
        
        Args:
            event: Any Pydantic model instance with model_dump_json()
        """
        self._persist_event(event)
        if self.callback:
            self.callback(event)

    def get_persisted_events(self) -> list[dict]:
        """Retrieve all persisted events for this job from Redis.
        
        Returns:
            List of event dictionaries, empty list if no events found
        """
        try:
            events_json_list = self.redis.lrange(self.events_key, 0, -1)
            return [json.loads(event_json) for event_json in events_json_list]
        except Exception as e:
            logger.error(f"Failed to retrieve persisted events: {e}", exc_info=True)
            return []

    def get_event_count(self) -> int:
        """Get total number of persisted events for this job.
        
        Returns:
            Number of events in Redis list
        """
        try:
            return self.redis.llen(self.events_key)
        except Exception as e:
            logger.error(f"Failed to get event count: {e}", exc_info=True)
            return 0

    def clear_events(self) -> None:
        """Clear all persisted events for this job.
        
        Useful for cleanup or testing. Events expire after 24 hours automatically.
        """
        try:
            self.redis.delete(self.events_key)
            logger.info(f"Cleared all events for job {self.job_id}")
        except Exception as e:
            logger.error(f"Failed to clear events: {e}", exc_info=True)
