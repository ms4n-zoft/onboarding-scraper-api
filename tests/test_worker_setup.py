"""Quick verification test for worker setup.

This script verifies that the worker configuration is correct without
actually running a job. It checks imports, dependencies, and connections.
"""
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Configure logging
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_worker_setup():
    """Verify worker setup is correct."""
    logger.info("=" * 80)
    logger.info("Worker Setup Verification")
    logger.info("=" * 80)
    
    # Test 1: Import worker module
    logger.info("\n✓ Test 1: Importing worker module...")
    try:
        import worker
        logger.success("  ✓ Worker module imported successfully")
    except Exception as e:
        logger.error(f"  ✗ Failed to import worker: {e}")
        return False
    
    # Test 2: Check Redis connection
    logger.info("\n✓ Test 2: Testing Redis connection...")
    try:
        from src.config.redis import get_redis_connection
        redis_conn = get_redis_connection(decode_responses=False)
        redis_conn.ping()
        logger.success("  ✓ Redis connection successful")
    except Exception as e:
        logger.error(f"  ✗ Redis connection failed: {e}")
        return False
    
    # Test 3: Check RQ Queue
    logger.info("\n✓ Test 3: Testing RQ Queue...")
    try:
        from rq import Queue
        queue = Queue("scraper", connection=redis_conn)
        queue_size = len(queue)
        logger.success(f"  ✓ Queue accessible (current size: {queue_size})")
    except Exception as e:
        logger.error(f"  ✗ Queue check failed: {e}")
        return False
    
    # Test 4: Check scraper task import
    logger.info("\n✓ Test 4: Testing scraper task import...")
    try:
        from src.jobs.scraper_task import scrape_product_job
        logger.success("  ✓ Scraper task imported successfully")
    except Exception as e:
        logger.error(f"  ✗ Scraper task import failed: {e}")
        return False
    
    # Test 5: Check dependencies
    logger.info("\n✓ Test 5: Checking dependencies...")
    try:
        from src.dependencies import get_queue, get_rq_redis_client, get_redis_client
        test_queue = get_queue()
        rq_client = get_rq_redis_client()
        json_client = get_redis_client()
        logger.success("  ✓ All dependencies accessible")
    except Exception as e:
        logger.error(f"  ✗ Dependency check failed: {e}")
        return False
    
    # Test 6: Check logs directory
    logger.info("\n✓ Test 6: Checking logs directory...")
    try:
        log_dir = Path("logs")
        if not log_dir.exists():
            log_dir.mkdir()
            logger.info("  ✓ Created logs directory")
        else:
            logger.success("  ✓ Logs directory exists")
    except Exception as e:
        logger.error(f"  ✗ Logs directory check failed: {e}")
        return False
    
    # Test 7: Verify worker can be initialized (without starting)
    logger.info("\n✓ Test 7: Testing worker initialization...")
    try:
        from rq import Worker
        worker_instance = Worker(
            [queue],
            connection=redis_conn,
            name="test-worker",
        )
        logger.success(f"  ✓ Worker can be initialized")
        logger.info(f"    - Worker name: {worker_instance.name}")
        logger.info(f"    - Queues: {[q.name for q in worker_instance.queues]}")
    except Exception as e:
        logger.error(f"  ✗ Worker initialization failed: {e}")
        return False
    
    # All tests passed
    logger.info("\n" + "=" * 80)
    logger.success("✅ All verification tests passed!")
    logger.info("=" * 80)
    logger.info("\nYou can now start the worker with:")
    logger.info("  python worker.py")
    logger.info("\nTo test with an actual job:")
    logger.info("  python tests/test_worker_manual.py")
    logger.info("")
    
    return True


if __name__ == "__main__":
    try:
        success = test_worker_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nVerification failed: {e}", exc_info=True)
        sys.exit(1)
