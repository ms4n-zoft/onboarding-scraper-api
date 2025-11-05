"""Agentic analyzer using function calling for product extraction."""
from __future__ import annotations

import json
from typing import Callable, Any
from openai import AzureOpenAI
from loguru import logger

from ..schemas.product import ProductSnapshot
from ..utils.event_emitter import EventEmitter
from .tools.fetcher import fetch_page_text, get_fetch_page_text_tool
from .utils.tool_handler import ToolHandler, ToolRegistry


AGENTIC_SYSTEM_PROMPT = (
    "You are a product intelligence extractor. Extract structured product data from web pages to populate a ProductSnapshot.\n\n"
    "INSTRUCTIONS:\n"
    "1. Use fetch_page_text tool strategically to gather information from multiple relevant pages.\n"
    "2. Prioritize pages: homepage, about, features, pricing, contact, security/compliance.\n"
    "3. For optional fields: always attempt to find them. Only omit if absolutely unavailable from the sources.\n"
    "4. Never fabricate data - only use verified information from fetched content.\n"
    "5. Write in neutral, professional, third-person tone.\n"
    "6. Keep numeric values as numbers (e.g., 2023, 4.5).\n"
    "7. All URLs must begin with https:// and be copy-paste ready.\n"
    "8. For pricing: CRITICAL - Always fetch the dedicated pricing page (e.g., /pricing, /plans, /pricing-plans). Extract all available plans with plan name, amount, currency, period, and included features. Include free tiers and trials.\n"
    "9. Return empty lists/nulls only when information truly cannot be found after thorough search.\n\n"
    "OUTPUT: Valid JSON matching the ProductSnapshot schema exactly."
)


def extract_product_snapshot_agentic(
    client: AzureOpenAI,
    deployment: str,
    initial_url: str,
    event_callback: Callable[[Any], None] | None = None,
) -> ProductSnapshot:
    """Extract product data using agentic function calling.

    Args:
        client: Azure OpenAI client
        deployment: Model deployment name
        initial_url: URL to scrape
        event_callback: Optional callback for streaming events (SSE)

    Returns:
        ProductSnapshot with extracted product data
    """
    logger.info(f"Starting agentic extraction for URL: {initial_url}")

    # Setup event emitter
    emitter = EventEmitter(event_callback)
    emitter.emit_start()

    # Setup tool registry and handler
    registry = ToolRegistry()
    registry.register(
        "fetch_page_text",
        get_fetch_page_text_tool(),
        fetch_page_text
    )
    tool_handler = ToolHandler(registry)
    
    tools = registry.get_all_schemas()
    logger.debug(f"Registered {len(tools)} tool(s)")
    
    messages = [
        {
            "role": "system",
            "content": AGENTIC_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": (
                f"Extract product information and create a ProductSnapshot from this URL: {initial_url}\n\n"
                "Use the fetch_page_text tool to retrieve content from the URL and any related pages you need. "
                "Then provide your analysis in the ProductSnapshot format as a valid JSON object.\n\n"
                "Only return valid JSON for the ProductSnapshot, no other text. "
                "Make sure to use the fetch_page_text tool to get the actual page content before analyzing."
            )
        }
    ]
    
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.debug(f"Agentic loop iteration {iteration}/{max_iterations}")

        response = client.beta.chat.completions.parse(
            model=deployment,
            messages=messages,
            tools=tools,
            response_format=ProductSnapshot,
        )

        if response.choices[0].message.tool_calls:
            tool_calls = response.choices[0].message.tool_calls
            logger.info(f"LLM called {len(tool_calls)} tool(s)")

            # Emit reading events for each page
            for tc in tool_calls:
                if tc.function.name == "fetch_page_text":
                    try:
                        args = json.loads(tc.function.arguments)
                        url = args.get("url")
                        if url:
                            emitter.emit_reading(url)
                    except Exception as e:
                        logger.warning(f"Failed to parse tool arguments: {e}")

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in tool_calls
                ]
            })

            tool_results = tool_handler.execute_parallel(tool_calls)
            tool_response_messages = tool_handler.build_tool_response_messages(tool_results)
            messages.extend(tool_response_messages)

            # Emit analyzing update after tools complete
            emitter.emit_update("Analyzing...")
        else:
            logger.debug("LLM produced final response (no tool calls)")
            parsed = response.choices[0].message.parsed
            if parsed:
                logger.info("Successfully extracted ProductSnapshot")
                return parsed
            logger.warning("LLM response parsed as None")
            break
    
    logger.error(f"Failed to extract after {max_iterations} iterations")
    raise RuntimeError(
        f"Failed to extract product snapshot after {max_iterations} iterations"
    )
