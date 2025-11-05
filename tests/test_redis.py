"""Test script for Redis connection."""
import sys
from pathlib import Path

# Add parent directory to path so src module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.config.redis import get_redis_connection
from loguru import logger


def test_redis_connection():
    """Test Redis connection and basic operations."""
    try:
        logger.info("Testing Redis connection...")
        redis_client = get_redis_connection()
        
        # Test basic operations
        test_key = "test:connection"
        test_value = "Hello Redis!"
        
        # Set a value
        redis_client.set(test_key, test_value, ex=60)  # Expires in 60 seconds
        logger.info(f"✓ Successfully set key: {test_key}")
        
        # Get the value back
        retrieved_value = redis_client.get(test_key)
        logger.info(f"✓ Successfully retrieved value: {retrieved_value}")
        
        # Verify
        assert retrieved_value == test_value, "Value mismatch!"
        logger.info("✓ Value matches!")
        
        # Clean up
        redis_client.delete(test_key)
        logger.info("✓ Cleaned up test key")
        
        # Test list operations (for events)
        list_key = "test:list"
        redis_client.rpush(list_key, "event1", "event2", "event3")
        logger.info(f"✓ Created list with 3 items")
        
        list_items = redis_client.lrange(list_key, 0, -1)
        logger.info(f"✓ Retrieved list items: {list_items}")
        
        redis_client.delete(list_key)
        logger.info("✓ Cleaned up test list")
        
        logger.success("🎉 All Redis tests passed!")
        return True
        
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.info("Please set REDIS_URL in your .env file")
        return False
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return False


if __name__ == "__main__":
    test_redis_connection()
