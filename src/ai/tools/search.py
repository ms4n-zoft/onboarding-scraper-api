"""Tool for web search using Tavily API via function calling."""
from __future__ import annotations

import json
from loguru import logger

from ...config.tavily import load_tavily_client

# Shared Tavily client instance to maintain key rotation state
_tavily_client = None


def _get_tavily_client():
    """Get or create the shared Tavily client instance."""
    global _tavily_client
    if _tavily_client is None:
        _tavily_client = load_tavily_client()
    return _tavily_client


def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using Tavily API (basic search for cost efficiency)."""
    if not query or not query.strip():
        return json.dumps({"success": False, "error": "Search query cannot be empty"})
    
    if len(query) > 400:
        return json.dumps({"success": False, "error": "Search query must be less than 400 characters"})
    
    if not isinstance(max_results, int) or max_results < 1:
        max_results = 5
    elif max_results > 10:
        max_results = 10
    
    try:
        logger.info(f"[search_web] query_len={len(query)}, max_results={max_results}")
        tavily_client = _get_tavily_client()
        response = tavily_client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            include_images=False
        )
        
        formatted_response = {
            "success": True,
            "query": response.get("query"),
            "answer": response.get("answer"),
            "results": [
                {
                    "title": result.get("title"),
                    "url": result.get("url"),
                    "content": result.get("content"),
                    "score": result.get("score")
                }
                for result in response.get("results", [])
            ],
            "results_count": len(response.get("results", [])),
            "response_time": response.get("response_time")
        }
        # Log a brief summary of results (first up to 3 URLs)
        urls_preview = [r.get("url") for r in response.get("results", [])[:3]]
        logger.info(f"[search_web] results_count={formatted_response['results_count']}, preview_urls={urls_preview}")
        return json.dumps(formatted_response, indent=2)
    except Exception as e:
        logger.error(f"Web search failed: {str(e)}")
        return json.dumps({"success": False, "error": str(e)})


def get_web_search_tool() -> dict:
    """Function schema for search_web (to be wrapped by the caller)."""
    return {
        "name": "search_web",
        "description": "Search the internet for relevant information and richer data to enhance content quality and context.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query (max 400 characters)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1-10, default: 5)",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5
                }
            },
            "required": ["query", "max_results"],
            "additionalProperties": False
        },
        "strict": True
    }
