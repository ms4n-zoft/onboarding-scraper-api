#!/usr/bin/env python3
"""RQ Worker for processing scraping jobs.

This worker processes background scraping jobs from the Redis queue.
It handles job execution, logging, and exception handling.

Usage:
    python worker.py
    
    # Or with custom configuration:
    RQ_WORKER_NAME=worker-1 python worker.py
    
Environment Variables:
    REDIS_URL: Redis connection URL (required)
    RQ_WORKER_NAME: Custom worker name (optional, default: hostname-timestamp)
    RQ_WORKER_BURST: Run in burst mode - exit after all jobs processed (optional)
"""
import sys
import os
import signal
import socket
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from loguru import logger
from rq import Worker, Queue
from rq.job import Job

from src.config.redis import get_redis_connection
from src.utils.env import get_env_var

# Load environment variables
load_dotenv()


def configure_logging():
    """Configure loguru logging for the worker."""
    # Remove default handler
    logger.remove()
    
    # Add console handler with custom format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )
    
    # Add file handler for persistent logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "worker_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # Rotate at midnight
        retention="30 days",  # Keep logs for 30 days
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    logger.info("Worker logging configured")


def exception_handler(job: Job, exc_type, exc_value, traceback):
    """Custom exception handler for failed jobs.
    
    This handler is called when a job fails. It logs the error and
    ensures the job status is properly updated.
    
    Args:
        job: The RQ Job that failed
        exc_type: Exception type
        exc_value: Exception instance
        traceback: Exception traceback
    """
    logger.error(f"Job {job.id} failed with {exc_type.__name__}: {exc_value}")
    logger.error(f"Job function: {job.func_name}")
    logger.error(f"Job args: {job.args}")
    logger.error(f"Job kwargs: {job.kwargs}")
    
    # The exception info is automatically stored by RQ in job.exc_info
    # We just need to ensure proper logging
    return True  # Return True to mark the job as failed


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    logger.warning(f"Received signal {signal_name}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Start the RQ worker."""
    configure_logging()
    
    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get worker configuration
    # Use hostname + timestamp as default to ensure uniqueness
    default_worker_name = f"{socket.gethostname()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    worker_name = get_env_var("RQ_WORKER_NAME", default=default_worker_name)
    burst_mode = get_env_var("RQ_WORKER_BURST", default="false").lower() == "true"
    
    logger.info("=" * 80)
    logger.info("Starting RQ Worker for Product Scraper Engine")
    logger.info("=" * 80)
    
    logger.info(f"Worker name: {worker_name}")
    logger.info(f"Burst mode: {burst_mode}")
    logger.info(f"Queue: scraper")
    
    try:
        # Get Redis connection for RQ (without decode_responses)
        redis_conn = get_redis_connection(decode_responses=False)
        
        # Create queue
        queue = Queue("scraper", connection=redis_conn)
        
        logger.info(f"Connected to Redis")
        logger.info(f"Queue size: {len(queue)} jobs")
        
        # Create worker
        worker = Worker(
            [queue],
            connection=redis_conn,
            name=worker_name,
            exception_handlers=[exception_handler],
        )
        
        logger.success("Worker initialized successfully")
        logger.info("Waiting for jobs...")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Start processing jobs
        worker.work(
            burst=burst_mode,
            logging_level="INFO",
            max_jobs=None,  # Process unlimited jobs
            with_scheduler=False,  # We don't need the scheduler
        )
            
    except KeyboardInterrupt:
        logger.info("\nWorker stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed to start: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
