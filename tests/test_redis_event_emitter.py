"""Test script for Redis Event Emitter."""
import sys
from pathlib import Path

# Add parent directory to path so src module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import json
from src.config.redis import get_redis_connection
from src.utils.redis_event_emitter import RedisEventEmitter
from src.schemas.events import EventType
from loguru import logger


def test_redis_event_emitter():
    """Test Redis Event Emitter functionality."""
    logger.info("Starting Redis Event Emitter tests...\n")
    
    try:
        redis_client = get_redis_connection()
        job_id = "test-job-emitter-001"
        
        # Clean up any previous test data
        emitter = RedisEventEmitter(job_id, redis_client)
        emitter.clear_events()
        logger.info(f"✓ Cleaned up previous test data for job: {job_id}\n")
        
        # Test 1: Emit events without callback
        logger.info("Test 1: Emitting events without callback...")
        emitter.emit_start()
        emitter.emit_reading("https://example.com/pricing")
        emitter.emit_update("Analyzing pricing information...")
        logger.info(f"✓ Emitted 3 events\n")
        
        # Test 2: Retrieve persisted events
        logger.info("Test 2: Retrieving persisted events from Redis...")
        events = emitter.get_persisted_events()
        logger.info(f"✓ Retrieved {len(events)} events from Redis")
        
        for i, event in enumerate(events, 1):
            logger.info(f"  Event {i}: {event['event']} - {event.get('message', event.get('url', ''))}")
        
        assert len(events) == 3, f"Expected 3 events, got {len(events)}"
        assert events[0]["event"] == EventType.START
        assert events[1]["event"] == EventType.READING
        assert events[2]["event"] == EventType.UPDATE
        logger.info("✓ All events are correct type and order\n")
        
        # Test 3: Event count
        logger.info("Test 3: Checking event count...")
        count = emitter.get_event_count()
        assert count == 3, f"Expected 3 events, got {count}"
        logger.info(f"✓ Event count is correct: {count}\n")
        
        # Test 4: Emit with callback
        logger.info("Test 4: Emitting with callback...")
        collected_events = []
        
        def event_callback(event):
            collected_events.append(event)
        
        emitter_with_callback = RedisEventEmitter(job_id, redis_client, callback=event_callback)
        # Don't clear - we want to add more events to existing ones
        emitter_with_callback.emit_update("Extracting features...")
        
        assert len(collected_events) == 1, "Callback should have been called once"
        logger.info(f"✓ Callback was invoked: {collected_events[0].message}\n")
        
        # Test 5: Complete event with data
        logger.info("Test 5: Emitting complete event with data...")
        result_data = {
            "product_name": "Example Product",
            "company_name": "Example Inc",
            "description": "A great product"
        }
        emitter_with_callback.emit_complete(data=result_data)
        
        assert collected_events[-1].event == EventType.COMPLETE
        assert collected_events[-1].data == result_data
        logger.info(f"✓ Complete event with data: {collected_events[-1].message}\n")
        
        # Test 6: Error event
        logger.info("Test 6: Emitting error event...")
        emitter_with_callback.emit_error(
            message="Scraping failed",
            error="HTTPError: 404 Not Found"
        )
        
        assert collected_events[-1].event == EventType.ERROR
        logger.info(f"✓ Error event emitted: {collected_events[-1].message}\n")
        
        # Test 7: Verify all events in Redis
        logger.info("Test 7: Verifying all events persisted in Redis...")
        all_events = emitter.get_persisted_events()
        logger.info(f"✓ Total events in Redis: {len(all_events)}")
        
        event_types = [e["event"] for e in all_events]
        logger.info(f"  Event sequence: {' → '.join(event_types)}\n")
        
        # Test 8: Multiple jobs isolation
        logger.info("Test 8: Testing job isolation...")
        job_id_2 = "test-job-emitter-002"
        emitter_2 = RedisEventEmitter(job_id_2, redis_client)
        emitter_2.clear_events()
        
        emitter_2.emit_start()
        events_job_2 = emitter_2.get_persisted_events()
        
        assert len(events_job_2) == 1, "Job 2 should only have 1 event"
        assert len(emitter.get_persisted_events()) > 1, "Job 1 events should be separate"
        logger.info(f"✓ Job isolation working correctly\n")
        
        # Cleanup
        logger.info("Cleaning up test data...")
        emitter.clear_events()
        emitter_2.clear_events()
        logger.info("✓ Test data cleaned up\n")
        
        logger.success("🎉 All Redis Event Emitter tests passed!")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_redis_event_emitter()
    exit(0 if success else 1)
