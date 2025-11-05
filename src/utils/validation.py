"""URL validation utilities."""
from __future__ import annotations

from urllib.parse import urlparse
from fastapi import HTTPException


def validate_scrape_url(url: str) -> str:
    """Validate URL to prevent SSRF attacks.
    
    Args:
        url: URL to validate
        
    Returns:
        The validated URL
        
    Raises:
        HTTPException: If URL is invalid or potentially malicious
    """
    try:
        parsed = urlparse(url)
        
        # Only allow http/https
        if parsed.scheme not in ["http", "https"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL scheme: {parsed.scheme}. Only http and https are allowed."
            )
        
        # Block private IPs and localhost
        if parsed.hostname:
            hostname_lower = parsed.hostname.lower()
            
            # Block localhost variations
            if hostname_lower in ["localhost", "127.0.0.1", "0.0.0.0", "::1"]:
                raise HTTPException(
                    status_code=400,
                    detail="Localhost URLs are not allowed"
                )
            
            # Block private IP ranges (basic check)
            if (hostname_lower.startswith("192.168.") or 
                hostname_lower.startswith("10.") or
                hostname_lower.startswith("172.16.") or
                hostname_lower.startswith("172.17.") or
                hostname_lower.startswith("172.18.") or
                hostname_lower.startswith("172.19.") or
                hostname_lower.startswith("172.20.") or
                hostname_lower.startswith("172.21.") or
                hostname_lower.startswith("172.22.") or
                hostname_lower.startswith("172.23.") or
                hostname_lower.startswith("172.24.") or
                hostname_lower.startswith("172.25.") or
                hostname_lower.startswith("172.26.") or
                hostname_lower.startswith("172.27.") or
                hostname_lower.startswith("172.28.") or
                hostname_lower.startswith("172.29.") or
                hostname_lower.startswith("172.30.") or
                hostname_lower.startswith("172.31.")):
                raise HTTPException(
                    status_code=400,
                    detail="Private IP addresses are not allowed"
                )
        
        # Must have a hostname
        if not parsed.hostname:
            raise HTTPException(
                status_code=400,
                detail="URL must have a valid hostname"
            )
        
        return url
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL format: {str(e)}"
        )
