"""Minimal entry point for agentic scraping prototype."""
from __future__ import annotations

import argparse
from typing import Callable, Any
from loguru import logger

from .config import load_azure_openai_client
from .ai.agentic_analyzer import extract_product_snapshot_agentic
from .utils.logging import configure_logging


def scrape_and_analyze(
    url: str,
    out_path: str | None = None,
    event_callback: Callable[[Any], None] | None = None,
) -> str:
    """Analyze a product page using agentic function calling.

    Args:
        url: Target URL to scrape
        out_path: Optional path to write JSON output
        event_callback: Optional callback for streaming events (SSE)

    Returns:
        JSON string of ProductSnapshot
    """
    client, deployment = load_azure_openai_client()
    result = extract_product_snapshot_agentic(
        client, deployment, url, event_callback=event_callback
    )

    payload = result.model_dump_json(indent=2, ensure_ascii=False)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(payload)

    return payload


def cli() -> None:
    """Parse command-line arguments and execute scraping workflow."""
    parser = argparse.ArgumentParser(description="Agentic product scraper")
    parser.add_argument("url", help="Target URL to scrape")
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional path to write JSON output",
    )
    parser.add_argument(
        "--log",
        type=str,
        default=None,
        help="Optional log file path",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )
    args = parser.parse_args()
    
    configure_logging(level=args.log_level, log_file=args.log)
    logger.info(f"Starting scraper for URL: {args.url}")
    
    result = scrape_and_analyze(args.url, args.out)
    print(result)


if __name__ == "__main__":
    cli()
