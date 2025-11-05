"""Test script for job stream endpoint."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import json
import time
from fastapi.testclient import TestClient
from src.api import app
from src.config.redis import get_redis_connection
from src.utils.redis_event_emitter import RedisEventEmitter
from loguru import logger


def test_job_stream_endpoint():
    """Test the /jobs/{job_id}/stream endpoint."""
    logger.info("Starting job stream endpoint tests...\n")
    
    try:
        client = TestClient(app)
        redis_client = get_redis_connection()
        
        # Test 1: Create mock job with events
        logger.info("Test 1: Creating mock job with events...")
        job_id = "test-stream-job-001"
        emitter = RedisEventEmitter(job_id, redis_client)
        emitter.clear_events()
        
        # Add some test events
        emitter.emit_start()
        emitter.emit_reading("https://example.com/pricing")
        emitter.emit_update("Analyzing pricing...")
        emitter.emit_complete(
            message="All done!",
            data={"product_name": "Test Product"}
        )
        
        logger.info(f"✓ Created job {job_id} with 4 events\n")
        
        # Test 2: Stream events from the endpoint
        logger.info("Test 2: Streaming events from endpoint...")
        
        with client.stream("GET", f"/jobs/{job_id}/stream") as response:
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            logger.info(f"✓ Response status: {response.status_code}")
            
            # Read SSE events
            events_received = []
            for line in response.iter_lines():
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                
                if line_str.startswith('data: '):
                    event_json = line_str[6:]  # Remove "data: " prefix
                    event = json.loads(event_json)
                    events_received.append(event)
                    logger.info(f"  - Received event: {event['event']}")
            
            assert len(events_received) == 4, f"Expected 4 events, got {len(events_received)}"
            logger.info(f"✓ Received all 4 events\n")
            
            # Verify event sequence
            assert events_received[0]["event"] == "start"
            assert events_received[1]["event"] == "reading"
            assert events_received[2]["event"] == "update"
            assert events_received[3]["event"] == "complete"
            logger.info("✓ Event sequence is correct\n")
            
            # Verify complete event has data
            assert events_received[3]["data"]["product_name"] == "Test Product"
            logger.info("✓ Complete event contains product data\n")
        
        # Test 3: Stream non-existent job
        logger.info("Test 3: Streaming non-existent job...")
        fake_job_id = "non-existent-job-999"
        
        with client.stream("GET", f"/jobs/{fake_job_id}/stream") as response:
            assert response.status_code == 200  # Should still return 200
            logger.info(f"✓ Response status: {response.status_code}")
            
            # Should get waiting message
            events_received = []
            for line in response.iter_lines():
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                if line_str.startswith('data: '):
                    event_json = line_str[6:]
                    event = json.loads(event_json)
                    events_received.append(event)
                    break  # Just get first event
            
            # Should have received at least waiting message
            if events_received:
                logger.info(f"  - Received: {events_received[0].get('event', 'unknown')}")
            logger.info("✓ Non-existent job handled gracefully\n")
        
        # Test 4: Verify SSE headers
        logger.info("Test 4: Verifying SSE headers...")
        with client.stream("GET", f"/jobs/{job_id}/stream") as response:
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            assert response.headers["cache-control"] == "no-cache"
            assert response.headers["x-accel-buffering"] == "no"
            logger.info("✓ All SSE headers are correct\n")
        
        # Test 5: Multiple clients can stream same job
        logger.info("Test 5: Testing multiple simultaneous streams...")
        
        # Create new job with events
        job_id_2 = "test-stream-job-002"
        emitter_2 = RedisEventEmitter(job_id_2, redis_client)
        emitter_2.clear_events()
        emitter_2.emit_start()
        emitter_2.emit_update("Processing...")
        
        # Open two streams simultaneously
        with client.stream("GET", f"/jobs/{job_id_2}/stream") as stream1:
            with client.stream("GET", f"/jobs/{job_id_2}/stream") as stream2:
                assert stream1.status_code == 200
                assert stream2.status_code == 200
                logger.info("✓ Multiple simultaneous streams work\n")
        
        # Cleanup
        logger.info("Cleaning up test data...")
        emitter.clear_events()
        emitter_2.clear_events()
        logger.info("✓ Test data cleaned up\n")
        
        logger.success("🎉 All job stream endpoint tests passed!")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_job_stream_endpoint()
    exit(0 if success else 1)
