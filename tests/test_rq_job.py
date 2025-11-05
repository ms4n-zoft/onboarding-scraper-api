"""Test script for RQ job function and worker task."""
import sys
from pathlib import Path

# Add parent directory to path so src module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import json
from unittest.mock import Mock, patch, MagicMock
from src.config.redis import get_redis_connection
from src.utils.redis_event_emitter import RedisEventEmitter
from src.schemas.product import ProductSnapshot
from src.schemas.events import EventType
from loguru import logger


def test_job_execution_simulation():
    """Simulate job execution to verify event persistence and result storage."""
    logger.info("Starting RQ job execution simulation test...\n")
    
    try:
        redis_client = get_redis_connection()
        job_id = "test-job-execution-001"
        source_url = "https://example.com/product"
        
        # Clean up any previous test data
        emitter = RedisEventEmitter(job_id, redis_client)
        emitter.clear_events()
        result_key = f"job:{job_id}:result"
        redis_client.delete(result_key)
        logger.info(f"✓ Cleaned up previous test data\n")
        
        # Test 1: Simulate job events during scraping
        logger.info("Test 1: Simulating job events...")
        
        # Simulate start event
        emitter.emit_start()
        logger.info("  - emit_start()")
        
        # Simulate reading events
        emitter.emit_reading("https://example.com/pricing")
        logger.info("  - emit_reading('https://example.com/pricing')")
        
        emitter.emit_reading("https://example.com/about")
        logger.info("  - emit_reading('https://example.com/about')")
        
        # Simulate update events
        emitter.emit_update("Analyzing pricing information...")
        logger.info("  - emit_update('Analyzing pricing information...')")
        
        emitter.emit_update("Extracting company details...")
        logger.info("  - emit_update('Extracting company details...')")
        
        logger.info("✓ All job events emitted\n")
        
        # Test 2: Verify events are in Redis
        logger.info("Test 2: Verifying events persisted in Redis...")
        events = emitter.get_persisted_events()
        assert len(events) == 5, f"Expected 5 events, got {len(events)}"
        logger.info(f"✓ Found {len(events)} events in Redis")
        
        event_types = [e["event"] for e in events]
        logger.info(f"  Event sequence: {' → '.join(event_types)}\n")
        
        # Test 3: Store result in Redis (simulating job completion)
        logger.info("Test 3: Storing job result in Redis...")
        
        # Create a mock ProductSnapshot
        mock_result = {
            "product_name": "Example Product",
            "company_name": "Example Inc",
            "description": "A great product for everything",
            "tagline": "Do everything better",
            "website_url": "https://example.com",
            "logo_url": "https://example.com/logo.png",
            "headquarters_location": "San Francisco, CA",
            "founding_year": 2020,
            "company_size": "50-100",
            "categories": ["SaaS", "Productivity"],
            "target_audiences": ["Businesses", "Developers"],
            "key_features": ["Feature 1", "Feature 2", "Feature 3"],
            "integrations": ["Zapier", "Slack"],
            "supported_platforms": ["Web", "Mobile"],
            "languages_supported": ["English"],
            "pricing_plans": [
                {
                    "plan_name": "Starter",
                    "price_amount": 29,
                    "price_currency": "USD",
                    "billing_period": "monthly",
                    "features_included": ["Feature 1", "Feature 2"]
                },
                {
                    "plan_name": "Pro",
                    "price_amount": 79,
                    "price_currency": "USD",
                    "billing_period": "monthly",
                    "features_included": ["Feature 1", "Feature 2", "Feature 3"]
                }
            ],
            "social_media": {
                "twitter": "https://twitter.com/example",
                "linkedin": "https://linkedin.com/company/example",
                "facebook": None,
                "github": "https://github.com/example"
            },
            "reviews": [
                {
                    "platform": "G2",
                    "rating": 4.5,
                    "review_count": 250,
                    "review_url": "https://g2.com/products/example"
                }
            ],
            "security_compliance": ["SOC 2", "GDPR"],
            "api_available": True,
            "free_trial_available": True,
            "support_channels": ["Email", "Chat", "Phone"]
        }
        
        result_json = json.dumps(mock_result, indent=2, ensure_ascii=False)
        redis_client.set(result_key, result_json, ex=86400)  # 24h expiration
        logger.info(f"✓ Stored result in Redis with key: {result_key}")
        logger.info(f"✓ Result size: {len(result_json)} bytes\n")
        
        # Test 4: Emit completion event with result
        logger.info("Test 4: Emitting completion event with result...")
        emitter.emit_complete(
            message="All done! Your product information is ready",
            data=mock_result
        )
        
        # Verify completion event
        all_events = emitter.get_persisted_events()
        last_event = all_events[-1]
        assert last_event["event"] == EventType.COMPLETE
        assert last_event["data"]["product_name"] == "Example Product"
        logger.info(f"✓ Completion event stored with product: {last_event['data']['product_name']}\n")
        
        # Test 5: Verify result can be retrieved
        logger.info("Test 5: Retrieving result from Redis...")
        stored_result_json = redis_client.get(result_key)
        assert stored_result_json is not None, "Result not found in Redis"
        
        stored_result = json.loads(stored_result_json)
        assert stored_result["product_name"] == "Example Product"
        assert len(stored_result["pricing_plans"]) == 2
        logger.info(f"✓ Retrieved result successfully")
        logger.info(f"  - Product: {stored_result['product_name']}")
        logger.info(f"  - Company: {stored_result['company_name']}")
        logger.info(f"  - Plans: {len(stored_result['pricing_plans'])}\n")
        
        # Test 6: Simulate job failure and error event
        logger.info("Test 6: Simulating job failure...")
        job_id_fail = "test-job-execution-fail-001"
        emitter_fail = RedisEventEmitter(job_id_fail, redis_client)
        emitter_fail.clear_events()
        
        emitter_fail.emit_start()
        emitter_fail.emit_reading("https://example.com/fail")
        emitter_fail.emit_error(
            message="Scraping failed",
            error="HTTPError: 503 Service Unavailable"
        )
        
        fail_events = emitter_fail.get_persisted_events()
        assert fail_events[-1]["event"] == EventType.ERROR
        logger.info(f"✓ Error event stored: {fail_events[-1]['error']}\n")
        
        # Test 7: Verify TTL is set on event key
        logger.info("Test 7: Verifying Redis TTL (expiration)...")
        ttl = redis_client.ttl(emitter.events_key)
        assert ttl > 0, "TTL should be greater than 0"
        logger.info(f"✓ Event key TTL: {ttl} seconds (~{ttl//3600} hours)\n")
        
        # Test 8: Verify TTL is set on result key
        logger.info("Test 8: Verifying result key TTL...")
        result_ttl = redis_client.ttl(result_key)
        assert result_ttl > 0, "Result TTL should be greater than 0"
        logger.info(f"✓ Result key TTL: {result_ttl} seconds (~{result_ttl//3600} hours)\n")
        
        # Cleanup
        logger.info("Cleaning up test data...")
        emitter.clear_events()
        emitter_fail.clear_events()
        redis_client.delete(result_key)
        logger.info("✓ Test data cleaned up\n")
        
        logger.success("🎉 All RQ job execution tests passed!")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Assertion failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


def test_job_function_imports():
    """Test that job function can be imported without errors."""
    logger.info("Testing job function imports...\n")
    
    try:
        from src.jobs.scraper_task import scrape_product_job
        logger.info("✓ Successfully imported scrape_product_job\n")
        
        # Verify it's callable
        assert callable(scrape_product_job), "scrape_product_job should be callable"
        logger.info("✓ scrape_product_job is callable\n")
        
        # Check function signature
        import inspect
        sig = inspect.signature(scrape_product_job)
        params = list(sig.parameters.keys())
        assert "source_url" in params, "Should have source_url parameter"
        logger.info(f"✓ Function signature: scrape_product_job({', '.join(params)})\n")
        
        logger.success("🎉 Job function import tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success1 = test_job_function_imports()
    print()
    success2 = test_job_execution_simulation()
    
    exit(0 if success1 and success2 else 1)
