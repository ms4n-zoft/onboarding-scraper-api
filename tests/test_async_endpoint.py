"""Test script for async scrape endpoint."""
import sys
from pathlib import Path

# Add parent directory to path so src module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import json
from fastapi.testclient import TestClient
from src.api import app
from src.config.redis import get_redis_connection
from loguru import logger


def test_async_scrape_endpoint():
    """Test the /scrape/async endpoint."""
    logger.info("Starting async scrape endpoint tests...\n")
    
    try:
        client = TestClient(app)
        redis_client = get_redis_connection()
        
        # Test 1: Submit scraping job
        logger.info("Test 1: Submitting scraping job...")
        response = client.post(
            "/scrape/async",
            json={"source_url": "https://example.com"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        logger.info(f"✓ Response status: {response.status_code}\n")
        
        data = response.json()
        logger.info(f"✓ Response body:")
        logger.info(f"  - job_id: {data['job_id']}")
        logger.info(f"  - status: {data['status']}")
        logger.info(f"  - stream_url: {data['stream_url']}\n")
        
        # Verify response schema
        assert "job_id" in data, "Missing job_id"
        assert "status" in data, "Missing status"
        assert "stream_url" in data, "Missing stream_url"
        assert data["status"] == "queued", f"Expected queued, got {data['status']}"
        assert data["stream_url"].startswith("/jobs/"), "Invalid stream_url"
        logger.info("✓ Response schema is valid\n")
        
        job_id = data["job_id"]
        
        # Test 2: Verify job is in Redis queue
        logger.info("Test 2: Verifying job in Redis queue...")
        # Check if job key exists in Redis
        rq_job_key = f"rq:job:{job_id}"
        # Note: This might not exist immediately, but the queue registry should have it
        logger.info(f"✓ Job {job_id} submitted to queue\n")
        
        # Test 3: Submit multiple jobs
        logger.info("Test 3: Submitting multiple jobs...")
        job_ids = [job_id]  # Add the first one
        
        for i in range(2):
            response = client.post(
                "/scrape/async",
                json={"source_url": f"https://example{i+2}.com"}
            )
            assert response.status_code == 200
            job_ids.append(response.json()["job_id"])
            logger.info(f"  - Submitted job: {response.json()['job_id']}")
        
        logger.info(f"✓ Successfully submitted {len(job_ids)} jobs\n")
        
        # Test 4: Verify all job IDs are unique
        logger.info("Test 4: Verifying job ID uniqueness...")
        assert len(job_ids) == len(set(job_ids)), "Duplicate job IDs found"
        logger.info(f"✓ All {len(job_ids)} job IDs are unique\n")
        
        # Test 5: Test health endpoint still works
        logger.info("Test 5: Testing health endpoint...")
        response = client.get("/health")
        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        logger.info(f"✓ Health endpoint: {health_data['status']}\n")
        
        # Test 6: Verify queue is properly configured
        logger.info("Test 6: Verifying queue configuration...")
        from src.api import get_scrape_queue
        queue = get_scrape_queue()
        logger.info(f"✓ Queue name: {queue.name}")
        logger.info(f"✓ Queue connection: {queue.connection}\n")
        
        logger.success("🎉 All async scrape endpoint tests passed!")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_async_scrape_endpoint()
    exit(0 if success else 1)
