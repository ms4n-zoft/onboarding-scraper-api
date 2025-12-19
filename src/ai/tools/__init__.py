"""Tools for agentic scraping with function calling."""
from __future__ import annotations

from .fetcher import (
    get_fetch_page_text_tool,
    fetch_page_text,
    get_web_fetcher_tool,
    fetch_web_content
)
from .search import get_web_search_tool, search_web

__all__ = [
    "get_fetch_page_text_tool",
    "fetch_page_text",
    "get_web_fetcher_tool",
    "fetch_web_content",
    "get_web_search_tool",
    "search_web"
]

