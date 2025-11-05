"""Manual test for worker functionality.

This script submits a test job and monitors its progress.
Run this in one terminal while worker.py runs in another.

Usage:
    # Terminal 1:
    python worker.py
    
    # Terminal 2:
    python tests/test_worker_manual.py
"""
import sys
import time
import json
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger
from rq import Queue
from rq.job import Job as RQJob

from src.dependencies import get_rq_redis_client, get_redis_client

# Load environment variables
load_dotenv()

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_worker_flow():
    """Submit a test job and monitor its execution."""
    logger.info("=" * 80)
    logger.info("Testing Worker End-to-End Flow")
    logger.info("=" * 80)
    
    rq_redis_client = get_rq_redis_client()
    redis_client = get_redis_client()
    queue = Queue("scraper", connection=rq_redis_client)
    
    # Check queue status
    logger.info(f"\nQueue status:")
    logger.info(f"  - Jobs in queue: {len(queue)}")
    logger.info(f"  - Failed jobs: {queue.failed_job_registry.count}")
    
    # Submit a test job
    test_url = "https://www.leadspace.com/"
    logger.info(f"\n📤 Submitting job for URL: {test_url}")
    
    job = queue.enqueue(
        "src.jobs.scraper_task.scrape_product_job",
        test_url,
        job_timeout=600,
        result_ttl=86400,
    )
    
    job_id = job.id
    logger.success(f"✓ Job submitted with ID: {job_id}")
    logger.info(f"  - Status: {job.get_status()}")
    logger.info(f"  - Position in queue: {queue.get_job_position(job_id)}")
    
    # Monitor job progress
    logger.info(f"\n👀 Monitoring job progress...")
    logger.info("(Make sure worker.py is running in another terminal)\n")
    
    start_time = time.time()
    last_status = None
    event_count = 0
    
    while True:
        # Refresh job
        job = RQJob.fetch(job_id, connection=rq_redis_client)
        current_status = job.get_status()
        
        # Log status changes
        if current_status != last_status:
            elapsed = time.time() - start_time
            logger.info(f"[{elapsed:.1f}s] Status changed: {last_status} → {current_status}")
            last_status = current_status
        
        # Check for events in Redis
        events_key = f"scraper:job:{job_id}:events"
        current_event_count = redis_client.llen(events_key)
        if current_event_count > event_count:
            new_events = redis_client.lrange(events_key, event_count, -1)
            for event_json in new_events:
                event_data = json.loads(event_json)
                event_type = event_data.get("event", "unknown")
                message = event_data.get("message", "")
                logger.info(f"  📨 Event: {event_type} - {message}")
            event_count = current_event_count
        
        # Check if job is done
        if job.is_finished:
            elapsed = time.time() - start_time
            logger.success(f"\n✅ Job completed successfully in {elapsed:.1f}s!")
            
            # Get result
            result_key = f"scraper:job:{job_id}:result"
            result_json = redis_client.get(result_key)
            
            if result_json:
                result_data = json.loads(result_json)
                logger.info(f"\n📊 Result Summary:")
                logger.info(f"  - Product: {result_data.get('product_name', 'N/A')}")
                logger.info(f"  - Company: {result_data.get('company_name', 'N/A')}")
                logger.info(f"  - Website: {result_data.get('website', 'N/A')}")
                logger.info(f"  - Description: {result_data.get('description', 'N/A')[:100]}...")
            else:
                logger.warning("  ⚠️  No result found in Redis")
            
            break
        
        if job.is_failed:
            elapsed = time.time() - start_time
            logger.error(f"\n❌ Job failed after {elapsed:.1f}s")
            logger.error(f"  Exception: {job.exc_info}")
            break
        
        # Check for timeout (5 minutes)
        if time.time() - start_time > 300:
            logger.warning("\n⏰ Timeout reached (5 minutes)")
            logger.warning(f"  Last status: {current_status}")
            logger.warning(f"  Events received: {event_count}")
            break
        
        time.sleep(1)
    
    # Final statistics
    logger.info(f"\n" + "=" * 80)
    logger.info("Test Complete")
    logger.info(f"  - Job ID: {job_id}")
    logger.info(f"  - Final Status: {job.get_status()}")
    logger.info(f"  - Events Received: {event_count}")
    logger.info(f"  - Total Time: {time.time() - start_time:.1f}s")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        test_worker_flow()
    except KeyboardInterrupt:
        logger.info("\n\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\n\nTest failed: {e}", exc_info=True)
