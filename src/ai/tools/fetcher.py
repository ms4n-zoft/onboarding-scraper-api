"""Tool for fetching and extracting text from URLs via function calling."""
from __future__ import annotations

import json
import httpx
from bs4 import BeautifulSoup
from loguru import logger


def fetch_web_content(url: str) -> str:
    """Fetch a URL and extract its visible text content and links."""
    if not url.startswith(("http://", "https://")):
        return json.dumps({
            "success": False,
            "error": "URL must start with http:// or https://"
        })
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        with httpx.Client(follow_redirects=True, timeout=30.0, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
    except httpx.HTTPError as e:
        logger.error(f"[fetch_web_content] http error: {url} | {str(e)}")
        return json.dumps({"success": False, "error": f"Failed to fetch URL: {str(e)}"})
    
    soup = BeautifulSoup(html, "html.parser")
    
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()
    
    text_chunks = [chunk.strip() for chunk in soup.stripped_strings if chunk.strip()]
    text = "\n".join(text_chunks)
    
    links = []
    for link in soup.find_all("a", href=True):
        href = link.get("href", "").strip()
        link_text = link.get_text(strip=True)
        if href and href != "#":
            links.append({"href": href, "text": link_text if link_text else "[no text]"})
    
    return json.dumps({
        "success": True,
        "url": url,
        "text": text,
        "text_length": len(text),
        "links": links,
        "links_count": len(links)
    }, indent=2)


# Keep the old function name as an alias for backward compatibility
def fetch_page_text(url: str) -> str:
    """Legacy alias for fetch_web_content."""
    return fetch_web_content(url)


def get_web_fetcher_tool() -> dict:
    """Function schema for fetch_web_content (to be wrapped by the caller)."""
    return {
        "name": "fetch_web_content",
        "description": "Fetch a URL and extract its visible text content and links.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL (must start with http:// or https://)"
                }
            },
            "required": ["url"],
            "additionalProperties": False
        },
        "strict": True
    }


def get_fetch_page_text_tool() -> dict:
    """Legacy function schema for fetch_page_text - returns wrapped schema for OpenAI."""
    return {
        "type": "function",
        "function": get_web_fetcher_tool()
    }

