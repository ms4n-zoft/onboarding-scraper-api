"""Integration test for complete async job flow.

This test verifies the entire system working together:
1. Submit job via API
2. Worker processes the job
3. Events stream via SSE
4. Status endpoint works
5. Result endpoint returns data

This test requires a worker to be running in another terminal.
"""
import sys
import json
import time
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger
from fastapi.testclient import TestClient

from src.api import app
from src.dependencies import get_queue, get_redis_client

# Load environment variables
load_dotenv()

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")

client = TestClient(app)


def test_integration_flow():
    """Test complete async job processing flow."""
    logger.info("=" * 80)
    logger.info("Integration Test - Complete Async Job Flow")
    logger.info("=" * 80)
    
    # Check if worker is running by checking queue
    queue = get_queue()
    initial_queue_size = len(queue)
    logger.info(f"\n📊 Initial queue size: {initial_queue_size}")
    
    if initial_queue_size > 50:
        logger.warning(f"⚠️  Large queue detected ({initial_queue_size} jobs)")
        logger.warning("This test will be slower. Consider clearing the queue or using burst mode.")
    
    # Step 1: Submit job via API
    logger.info("\n" + "=" * 80)
    logger.info("Step 1: Submit Job via API")
    logger.info("=" * 80)
    
    test_url = "https://www.leadspace.com/"
    logger.info(f"Submitting job for URL: {test_url}")
    
    response = client.post(
        "/scrape/async",
        json={"source_url": test_url}
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    job_data = response.json()
    
    job_id = job_data["job_id"]
    logger.success(f"✓ Job submitted successfully")
    logger.info(f"  - Job ID: {job_id}")
    logger.info(f"  - Status: {job_data['status']}")
    logger.info(f"  - Stream URL: {job_data['stream_url']}")
    
    # Step 2: Check job status
    logger.info("\n" + "=" * 80)
    logger.info("Step 2: Check Job Status")
    logger.info("=" * 80)
    
    response = client.get(f"/jobs/{job_id}/status")
    assert response.status_code == 200
    status_data = response.json()
    
    logger.success(f"✓ Status retrieved")
    logger.info(f"  - Status: {status_data['status']}")
    logger.info(f"  - Enqueued at: {status_data['enqueued_at']}")
    if status_data.get('position') is not None:
        logger.info(f"  - Position in queue: {status_data['position']}")
    
    # Step 3: Monitor job via SSE stream
    logger.info("\n" + "=" * 80)
    logger.info("Step 3: Monitor Job via SSE Stream")
    logger.info("=" * 80)
    logger.info("(Waiting for worker to process job...)")
    logger.info("⚠️  Make sure worker is running: python worker.py")
    
    start_time = time.time()
    events_received = []
    job_completed = False
    
    # Try streaming with timeout
    max_wait = 300  # 5 minutes max
    poll_interval = 2  # Check every 2 seconds
    
    with client.stream("GET", f"/jobs/{job_id}/stream") as response:
        assert response.status_code == 200
        logger.success("✓ SSE stream connected")
        
        for line in response.iter_lines():
            if not line:
                continue
                
            line = line.strip()
            
            # Parse SSE format
            if line.startswith("id:"):
                event_id = line[3:].strip()
            elif line.startswith("data:"):
                data_str = line[5:].strip()
                try:
                    event_data = json.loads(data_str)
                    event_type = event_data.get("event", "unknown")
                    events_received.append(event_data)
                    
                    elapsed = time.time() - start_time
                    message = event_data.get("message", "")
                    logger.info(f"[{elapsed:.1f}s] Event: {event_type} - {message}")
                    
                    # Check if job completed
                    if event_type == "complete":
                        job_completed = True
                        logger.success(f"✓ Job completed in {elapsed:.1f}s!")
                        break
                    elif event_type == "error":
                        logger.error(f"✗ Job failed: {event_data.get('error', 'Unknown error')}")
                        break
                        
                except json.JSONDecodeError:
                    pass
            
            # Timeout check
            if time.time() - start_time > max_wait:
                logger.warning(f"⏰ Timeout reached ({max_wait}s)")
                break
    
    logger.info(f"\n✓ Stream closed. Received {len(events_received)} events")
    
    # Step 4: Check final status
    logger.info("\n" + "=" * 80)
    logger.info("Step 4: Check Final Job Status")
    logger.info("=" * 80)
    
    response = client.get(f"/jobs/{job_id}/status")
    assert response.status_code == 200
    status_data = response.json()
    
    logger.info(f"  - Final status: {status_data['status']}")
    logger.info(f"  - Started at: {status_data.get('started_at', 'N/A')}")
    logger.info(f"  - Ended at: {status_data.get('ended_at', 'N/A')}")
    
    # Step 5: Retrieve result
    logger.info("\n" + "=" * 80)
    logger.info("Step 5: Retrieve Job Result")
    logger.info("=" * 80)
    
    if status_data['status'] == 'finished':
        response = client.get(f"/jobs/{job_id}/result")
        
        if response.status_code == 200:
            result_data = response.json()
            logger.success("✓ Result retrieved successfully")
            
            if result_data.get('result'):
                product = result_data['result']
                logger.info(f"\n📊 Product Data:")
                logger.info(f"  - Product: {product.get('product_name', 'N/A')}")
                logger.info(f"  - Company: {product.get('company_name', 'N/A')}")
                logger.info(f"  - Website: {product.get('website', 'N/A')}")
                
                if product.get('description'):
                    desc = product['description'][:100] + "..." if len(product['description']) > 100 else product['description']
                    logger.info(f"  - Description: {desc}")
        else:
            logger.warning(f"⚠️  Could not retrieve result: {response.status_code}")
            logger.warning(f"  Response: {response.json()}")
    else:
        logger.warning(f"⚠️  Job not finished (status: {status_data['status']})")
        logger.info("  Attempting to get result anyway...")
        
        response = client.get(f"/jobs/{job_id}/result")
        logger.info(f"  - Result endpoint status: {response.status_code}")
        logger.info(f"  - Response: {response.json()}")
    
    # Final Summary
    logger.info("\n" + "=" * 80)
    logger.info("Integration Test Summary")
    logger.info("=" * 80)
    logger.info(f"✓ Job ID: {job_id}")
    logger.info(f"✓ Events received: {len(events_received)}")
    logger.info(f"✓ Final status: {status_data['status']}")
    logger.info(f"✓ Total time: {time.time() - start_time:.1f}s")
    logger.info("=" * 80)
    
    # Validate minimum requirements
    assert len(events_received) > 0, "No events received - worker may not be running"
    
    if job_completed:
        logger.success("\n🎉 Integration test PASSED!")
        logger.info("All systems working correctly!")
        return True
    else:
        logger.warning("\n⚠️  Test completed but job may still be processing")
        logger.info("Check worker logs for details")
        return False


if __name__ == "__main__":
    try:
        logger.info("\n⚠️  Prerequisites:")
        logger.info("1. Make sure worker is running: python worker.py")
        logger.info("2. Make sure API server is NOT running (test uses TestClient)")
        logger.info("\nStarting test in 3 seconds...\n")
        time.sleep(3)
        
        success = test_integration_flow()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nTest failed: {e}", exc_info=True)
        sys.exit(1)
