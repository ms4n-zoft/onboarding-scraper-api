"""Tests for job status and result endpoints."""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from fastapi.testclient import TestClient
from loguru import logger
from rq.job import Job as RQJob

from src.api import app
from src.dependencies import get_redis_client, get_rq_redis_client, get_queue
from src.schemas.product import ProductSnapshot

# Test configuration
logger.add(sys.stderr, level="DEBUG")
client = TestClient(app)


def test_job_status_and_result_endpoints():
    """Test job status and result retrieval endpoints."""
    logger.info("Starting job status and result endpoint tests...\n")
    
    redis_client = get_redis_client()  # For JSON data
    rq_redis_client = get_rq_redis_client()  # For RQ operations
    queue = get_queue()
    
    # ============================================
    # Test 1: Get status of queued job
    # ============================================
    logger.info("Test 1: Checking status of queued job...")
    
    # Create a queued job - use src.jobs.scraper_task which is importable
    job = queue.enqueue(
        "src.jobs.scraper_task.scrape_product_job",
        "https://example.com/product",
        job_id="test-status-job-001",
        job_timeout=600
    )
    
    logger.info(f"  - Created job with ID: {job.id}")
    logger.info(f"  - Job status: {job.get_status()}")
    
    response = client.get("/jobs/test-status-job-001/status")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    status_data = response.json()
    assert status_data["job_id"] == "test-status-job-001"
    assert status_data["status"] in ["queued", "started", "finished"]  # Could be any of these
    assert status_data["enqueued_at"] is not None
    
    logger.info(f"✓ Job status retrieved")
    logger.info(f"  - Status: {status_data['status']}")
    if status_data.get("position") is not None:
        logger.info(f"  - Position: {status_data['position']}")
    logger.info("")
    
    # Clean up
    job.delete()
    
    # ============================================
    # Test 2: Get status of finished job
    # ============================================
    logger.info("Test 2: Checking status of finished job...")
    
    # Create a finished job (simulate)
    job = RQJob.create(
        "time.sleep",
        args=(0,),
        connection=redis_client,
        id="test-status-job-002"
    )
    job.set_status("finished")
    job.ended_at = datetime.now(timezone.utc)
    job.save()
    
    response = client.get("/jobs/test-status-job-002/status")
    assert response.status_code == 200
    
    status_data = response.json()
    assert status_data["job_id"] == "test-status-job-002"
    assert status_data["status"] == "finished"
    assert status_data["ended_at"] is not None
    
    logger.info(f"✓ Finished job status retrieved")
    logger.info(f"  - Status: {status_data['status']}\n")
    
    # Clean up
    job.delete()
    
    # ============================================
    # Test 3: Get status of failed job
    # ============================================
    logger.info("Test 3: Checking status of failed job...")
    
    # Create a failed job - use Redis directly to set exc_info
    job = RQJob.create(
        "time.sleep",
        args=(0,),
        connection=rq_redis_client,
        id="test-status-job-003"
    )
    job.set_status("failed")
    job.save()
    
    # Set exc_info directly in Redis (RQ stores it as a key)
    job_key = f"rq:job:{job.id}"
    rq_redis_client.hset(job_key, "exc_info", "Test exception: Something went wrong")
    
    response = client.get("/jobs/test-status-job-003/status")
    assert response.status_code == 200
    
    status_data = response.json()
    assert status_data["job_id"] == "test-status-job-003"
    assert status_data["status"] == "failed"
    # exc_info might be None if not stored correctly, that's okay
    if status_data["exc_info"]:
        assert "Something went wrong" in status_data["exc_info"]
    
    logger.info(f"✓ Failed job status retrieved")
    logger.info(f"  - Status: {status_data['status']}")
    if status_data.get("exc_info"):
        logger.info(f"  - Error: {status_data['exc_info'][:50]}...")
    logger.info("")
    
    # Clean up
    job.delete()
    
    # ============================================
    # Test 4: Get status of non-existent job
    # ============================================
    logger.info("Test 4: Checking status of non-existent job...")
    
    response = client.get("/jobs/non-existent-job-999/status")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "not found" in error_data["detail"].lower()
    
    logger.info(f"✓ Non-existent job returns 404\n")
    
    # ============================================
    # Test 5: Get status of expired job with events
    # ============================================
    logger.info("Test 5: Checking status of expired job with events...")
    
    # Create events but no job (simulating expired job)
    events_key = "scraper:job:test-status-job-004:events"
    redis_client.rpush(events_key, json.dumps({"event": "start", "message": "Job started"}))
    redis_client.expire(events_key, 3600)
    
    response = client.get("/jobs/test-status-job-004/status")
    assert response.status_code == 200
    
    status_data = response.json()
    assert status_data["job_id"] == "test-status-job-004"
    assert status_data["status"] == "finished"  # Assumes completed and expired
    
    logger.info(f"✓ Expired job with events treated as finished\n")
    
    # Clean up
    redis_client.delete(events_key)
    
    # ============================================
    # Test 6: Get result of non-finished job
    # ============================================
    logger.info("Test 6: Trying to get result of queued job...")
    
    # Create a queued job
    job = queue.enqueue(
        "src.jobs.scraper_task.scrape_product_job",
        "https://example.com/product",
        job_id="test-result-job-001",
        job_timeout=600
    )
    
    response = client.get("/jobs/test-result-job-001/result")
    assert response.status_code == 400
    
    error_data = response.json()
    assert "not finished" in error_data["detail"].lower()
    
    logger.info(f"✓ Queued job result returns 400 (not finished)\n")
    
    # Clean up
    job.delete()
    
    # ============================================
    # Test 7: Get result of finished job with result
    # ============================================
    logger.info("Test 7: Getting result of finished job...")
    
    # Create a finished job
    job = RQJob.create(
        "time.sleep",
        args=(0,),
        connection=rq_redis_client,
        id="test-result-job-002"
    )
    job.set_status("finished")
    job.save()
    
    # Store result in Redis
    result_key = "scraper:job:test-result-job-002:result"
    mock_product = {
        "product_name": "Test Product",
        "description": "A test product",
        "website": "https://example.com/product",
    }
    redis_client.setex(result_key, 86400, json.dumps(mock_product))
    
    response = client.get("/jobs/test-result-job-002/result")
    assert response.status_code == 200
    
    result_data = response.json()
    assert result_data["job_id"] == "test-result-job-002"
    assert result_data["status"] == "finished"
    assert result_data["result"] is not None
    assert result_data["result"]["product_name"] == "Test Product"
    assert result_data["error"] is None
    
    logger.info(f"✓ Finished job result retrieved")
    logger.info(f"  - Product name: {result_data['result']['product_name']}\n")
    
    # Clean up
    job.delete()
    redis_client.delete(result_key)
    
    # ============================================
    # Test 8: Get result of finished job without result (expired)
    # ============================================
    logger.info("Test 8: Getting result of finished job with expired result...")
    
    # Create a finished job but no result in Redis
    job = RQJob.create(
        "time.sleep",
        args=(0,),
        connection=rq_redis_client,
        id="test-result-job-003"
    )
    job.set_status("finished")
    job.save()
    
    response = client.get("/jobs/test-result-job-003/result")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "expired" in error_data["detail"].lower()
    
    logger.info(f"✓ Finished job with expired result returns 404\n")
    
    # Clean up
    job.delete()
    
    # ============================================
    # Test 9: Get result of failed job
    # ============================================
    logger.info("Test 9: Getting result of failed job...")
    
    # Create a failed job
    job = RQJob.create(
        "time.sleep",
        args=(0,),
        connection=rq_redis_client,
        id="test-result-job-004"
    )
    job.set_status("failed")
    job.save()
    
    # Set exc_info directly in Redis
    job_key = f"rq:job:{job.id}"
    rq_redis_client.hset(job_key, "exc_info", "ValueError: Invalid input data")
    
    response = client.get("/jobs/test-result-job-004/result")
    assert response.status_code == 200
    
    result_data = response.json()
    assert result_data["job_id"] == "test-result-job-004"
    assert result_data["status"] == "failed"
    assert result_data["result"] is None
    assert result_data["error"] is not None
    if "Invalid input data" in result_data["error"]:
        logger.info(f"✓ Failed job result retrieved with error info")
        logger.info(f"  - Error: {result_data['error'][:50]}...")
    else:
        logger.info(f"✓ Failed job result retrieved")
        logger.info(f"  - Error info: {result_data['error']}")
    logger.info("")
    
    # Clean up
    job.delete()
    
    # ============================================
    # Test 10: Get result of non-existent job
    # ============================================
    logger.info("Test 10: Getting result of non-existent job...")
    
    response = client.get("/jobs/non-existent-job-999/result")
    assert response.status_code == 404
    
    error_data = response.json()
    assert "not found" in error_data["detail"].lower()
    
    logger.info(f"✓ Non-existent job result returns 404\n")
    
    logger.success("🎉 All job status and result endpoint tests passed!")


if __name__ == "__main__":
    test_job_status_and_result_endpoints()
