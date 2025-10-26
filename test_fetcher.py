#!/usr/bin/env python
"""Quick test of fetch_page_text function."""
import json
import sys
from src.ai.tools.fetcher import fetch_page_text

url = "https://www.leadspace.com/"
print(f"Testing fetch_page_text with: {url}\n")

try:
    result = fetch_page_text(url)
    print("RAW RESULT:")
    print("=" * 80)
    print(result)
    print("=" * 80)
    print()
    
    result_dict = json.loads(result)
    
    print("=" * 80)
    print("TEST RESULT")
    print("=" * 80)
    print(f"Success: {result_dict['success']}")
    print(f"URL: {result_dict['url']}")
    print(f"Text Length: {result_dict['length']} chars")
    print(f"Number of Links Found: {len(result_dict.get('links', []))}")
    
    print("\n" + "=" * 80)
    print("FIRST 500 CHARS OF TEXT:")
    print("=" * 80)
    print(result_dict['text'][:500])
    
    print("\n" + "=" * 80)
    print("LINKS FOUND (first 15):")
    print("=" * 80)
    for i, link in enumerate(result_dict.get('links', [])[:15], 1):
        print(f"{i}. [{link['text'][:50]}] -> {link['href'][:60]}")
    
    remaining = len(result_dict.get('links', [])) - 15
    if remaining > 0:
        print(f"\n... and {remaining} more links")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
