"""Tavily API client configuration for web search with automatic fallback."""
from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from tavily import TavilyClient


class TavilyClientWithFallback:
    """Tavily client wrapper that automatically switches API keys on rate limits."""
    
    def __init__(self, api_keys: list[str]):
        if not api_keys:
            raise RuntimeError("At least one Tavily API key is required")
        self.api_keys = api_keys
        self.current_key_index = 0
        self._client = TavilyClient(api_key=self.api_keys[0])
        logger.info(f"Initialized Tavily with {len(api_keys)} API key(s)")
    
    def _switch_to_next_key(self) -> bool:
        """Switch to the next available API key. Returns True if switched, False if no more keys."""
        next_index = self.current_key_index + 1
        if next_index >= len(self.api_keys):
            return False
        
        self.current_key_index = next_index
        self._client = TavilyClient(api_key=self.api_keys[self.current_key_index])
        logger.warning(f"Switched to backup Tavily API key #{self.current_key_index + 1}")
        return True
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a rate limit error."""
        error_msg = str(error).lower()
        error_type = type(error).__name__.lower()
        
        rate_limit_indicators = [
            'rate limit', 'ratelimit', 'too many requests', 
            '429', 'quota exceeded', 'limit exceeded',
            'usage limit', 'forbidden', 'plan\'s set usage limit'
        ]
        
        return any(phrase in error_msg or phrase in error_type 
                   for phrase in rate_limit_indicators)
    
    def search(self, **kwargs: Any) -> dict:
        """Execute search with automatic fallback on rate limits."""
        attempts = 0
        max_attempts = len(self.api_keys)
        
        while attempts < max_attempts:
            try:
                logger.debug(f"Attempting search with Tavily key #{self.current_key_index + 1}/{len(self.api_keys)}")
                result = self._client.search(**kwargs)
                logger.debug(f"Search successful with key #{self.current_key_index + 1}")
                return result
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Tavily error (key #{self.current_key_index + 1}): {type(e).__name__}: {error_msg}")
                
                if self._is_rate_limit_error(e):
                    logger.warning(f"Rate limit/quota exceeded on key #{self.current_key_index + 1}")
                    if self._switch_to_next_key():
                        attempts += 1
                        logger.info(f"Retrying with key #{self.current_key_index + 1} (attempt {attempts + 1}/{max_attempts})")
                        continue
                    else:
                        logger.error("All Tavily API keys exhausted")
                        raise RuntimeError("All Tavily API keys have hit rate limits") from e
                else:
                    logger.error(f"Non-rate-limit error, not retrying: {error_msg}")
                    raise
        
        raise RuntimeError("Failed to execute search after exhausting all API keys")


def _get_tavily_api_keys() -> list[str]:
    """Load all available Tavily API keys from environment."""
    load_dotenv()
    
    keys = []
    primary_key = os.getenv("TAVILY_API_KEY")
    if primary_key:
        keys.append(primary_key)
    
    backup_keys_str = os.getenv("TAVILY_BACKUP_KEYS")
    if backup_keys_str:
        backup_keys = [k.strip() for k in backup_keys_str.split(",") if k.strip()]
        keys.extend(backup_keys)
    
    if not keys:
        raise RuntimeError("No Tavily API keys found. Set TAVILY_API_KEY or TAVILY_BACKUP_KEYS")
    
    return keys


def load_tavily_client() -> TavilyClientWithFallback:
    """Return a configured Tavily client with automatic fallback support.
    
    Requires env vars:
    - TAVILY_API_KEY: Primary API key
    - TAVILY_BACKUP_KEYS (optional): Comma-separated backup keys
    """
    api_keys = _get_tavily_api_keys()
    return TavilyClientWithFallback(api_keys)
