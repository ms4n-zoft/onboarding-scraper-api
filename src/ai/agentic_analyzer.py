"""Agentic analyzer using function calling for product extraction."""
from __future__ import annotations

import json
from typing import Callable, Any
from openai import AzureOpenAI
from loguru import logger

from ..schemas.product import ProductSnapshot
from ..utils.event_emitter import EventEmitter
from .tools.fetcher import fetch_page_text, get_fetch_page_text_tool, fetch_web_content, get_web_fetcher_tool
from .tools.search import search_web, get_web_search_tool
from .utils.tool_handler import ToolHandler, ToolRegistry


AGENTIC_SYSTEM_PROMPT = """You are a product intelligence extractor. Extract structured product data from the web to populate a ProductSnapshot. You can use tools (web search and web fetch) to gather additional authoritative evidence. You will be provided with an official homepage URL as your starting point. Your primary responsibility is to thoroughly explore this website and a small set of trusted external sources to fill in the ProductSnapshot schema comprehensively.

INSTRUCTIONS:
1. Use search_web and fetch_web_content tools strategically to gather information from multiple relevant pages.

2. Start by fetching the provided homepage URL to understand the product/company. Extract the product name, core description, and navigation structure from the homepage.

3. Systematically explore key pages on the official domain in this priority order: homepage, about, features/capabilities, pricing/plans, integrations, security/compliance, documentation/developers, FAQ, and contact. Look for sitemap or footer links to discover all relevant sections.

4. Use search_web to supplement information when needed - after extracting the product/company name from the homepage, search for external sources like press releases, news articles, industry reviews, funding announcements, and company profiles. Use queries like '[extracted_product_name] company', '[extracted_product_name] funding', '[extracted_product_name] features', etc.

5. For optional fields in the ProductSnapshot schema: always attempt to find them. Only omit if absolutely unavailable from the sources after reasonable effort.

5. Never fabricate data – only use verified information from fetched content. If information is conflicting, prefer official product or company sources and clearly ignore unverified claims.

6. Write in a neutral, professional, third-person tone.

7. Keep numeric values as numbers (e.g., 2023, 4.5).

8. All URLs must begin with https:// and be copy-paste ready.

9. For pricing: always attempt to identify the dedicated pricing page (e.g., /pricing, /plans, /pricing-plans) on the official site. Extract all available plans with plan name, billing entity, amount, currency, billing period, and included features. Include free tiers and trials where present. Map them into the PricingPlan and PricingInfo fields.

10. For review-related fields (ReviewSummary with strengths, weaknesses, overall_rating, review_sources): DEPRIORITIZE these fields. Review platforms (G2, Capterra, Trustpilot, etc.) often block automated access. If you encounter errors when trying to access reviews, skip them immediately and move on. Do not waste iterations retrying review sites. Only include reviews if they are easily accessible on the first attempt.

11. For company_info (overview, founding, funding_info, acquisitions, global_presence, company_culture, community, growth_story, valuation, product_expansion, recent_new_features, product_offerings): focus on factual, evidence-backed information derived from official pages. Leave fields empty only if the information cannot be reliably determined.

12. CRITICAL FIELDS REQUIRING EXTRA RESEARCH EFFORT:
   - ai_capabilities & ai_info: These fields are frequently overlooked but highly valuable. Actively search for AI/ML features, automation capabilities, intelligent recommendations, NLP, computer vision, predictive analytics, or any AI-powered functionality. Check product pages, features sections, technical documentation. Look for terms like 'AI', 'machine learning', 'artificial intelligence', 'smart', 'intelligent', 'automation', 'predictive'.
   - gcc_availability & gcc_info: Many products serve GCC (Gulf Cooperation Council) markets but don't advertise it prominently. Search for: regional offices in UAE/Saudi Arabia/Qatar/Kuwait/Bahrain/Oman, Arabic language support, GCC-specific customers or case studies, regional partnerships, data centers in the region, or compliance with regional regulations. Check 'locations', 'about us', 'customers', 'language options', and 'contact' pages.
   These four fields should NOT be left null without dedicated search effort. After extracting the product name from the homepage, use search queries like '[extracted_product_name] AI features', '[extracted_product_name] GCC customers', '[extracted_product_name] Arabic support'.

13. For other structured sub-objects:
   - contact: Extract phone_number, country_code, support_email, and address when available.
   - social_profiles: Prefer official LinkedIn, Twitter, and Facebook URLs.
   - web3_info: Identify whether the product/company is Web3-related and list any Web3 components.
   - integrations: Populate integration partners by name, website, and logo URL when possible.

14. For list fields (e.g., industry, features, deployment_options, support_options, languages_supported, technology_stack, product_offerings, strengths, weaknesses, compliance_standards, review_sources, integrations, pricing_plans): prefer concise but complete lists derived from the sources. Do not invent items.

15. Return empty lists/nulls only when information truly cannot be found after a focused search.

16. ITERATION BUDGET & COMPLETION TARGET: You have a total of 20 iterations to complete this task. Target 85-95% completion of the ProductSnapshot schema.
   - Iterations 1-15: Use tools freely (search_web, fetch_web_content) to research thoroughly and gather comprehensive information. Focus on official website content, not review platforms. Dedicate at least 1-2 tool calls to researching AI capabilities and GCC presence.
   - Iterations 16-19: Focus on refinement. Target high-priority missing fields with focused searches. Skip blocked/inaccessible sites.
   - Iteration 20: Final iteration without tools. Compile your best output based on all collected data.

17. ERROR HANDLING: If a fetch_web_content call fails (HTTP error, timeout, blocking), do NOT retry the same URL. Move on immediately to other sources. Do not waste iterations on blocked sites.

18. Prioritize quality over quantity - it's better to have 85-95% of fields accurately filled than to fabricate data to reach 100%.

19. Never fabricate data. If, after reasonable effort with the tools, specific information is not publicly available, leave that field as null or an empty list as appropriate.

20. Output must strictly match the ProductSnapshot schema; the response_format will enforce typing, but you must ensure all values are consistent with the schema constraints.
"""


def extract_product_snapshot_agentic(
    client: AzureOpenAI,
    llm_model: str,
    initial_url: str,
    event_callback: Callable[[Any], None] | None = None,
) -> ProductSnapshot:
    """Extract product data using agentic function calling.

    Args:
        client: Azure OpenAI client
        llm_model: LLM model name
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
    
    # Register web fetcher tool (use raw schema, registry wraps it)
    registry.register(
        "fetch_web_content",  # Match the name in the schema
        get_web_fetcher_tool(),
        fetch_web_content  # Use the actual function
    )
    
    # Register web search tool
    registry.register(
        "search_web",
        get_web_search_tool(),
        search_web
    )
    
    tool_handler = ToolHandler(registry)
    
    tools = registry.get_all_schemas()
    logger.info(f"Registered {len(tools)} tool(s)")
    
    messages = [
        {
            "role": "system",
            "content": AGENTIC_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": (
                f"TASK: Using the provided homepage URL, thoroughly explore the official website to build a complete, factually accurate ProductSnapshot instance for this product/company. Begin by fetching the homepage to understand the product identity, then systematically navigate through key pages (about, features, pricing, integrations, security, documentation, contact). Follow the system instructions carefully, and prefer official sources. If, after reasonable effort, specific information cannot be found, leave those fields null or empty lists as appropriate rather than guessing.\n\n"
                f"ITERATION BUDGET: You have 20 iterations total to complete this task. Plan your tool usage strategically. Target 85-95% completion of the ProductSnapshot schema - prioritize quality and accuracy over completeness. On the final iteration (20/20), you will no longer have access to tools - ensure you provide your best output based on data collected.\n\n"
                f"CONTEXT:\n"
                f"Official Homepage URL: {initial_url}\n\n"
                f"CRITICAL REMINDERS:\n"
                f"- Dedicate effort to finding ai_capabilities, ai_info, gcc_availability, and gcc_info fields\n"
                f"- Always fetch the pricing page (/pricing, /plans) for complete pricing information\n"
                f"- Skip review sites if they're blocked - don't waste iterations\n"
                f"- Use the fetch_web_content tool to retrieve actual page content\n"
                f"- Use the search_web tool to find external authoritative sources and supplementary information"
            )
        }
    ]
    
    max_iterations = 20
    
    for iteration_num in range(max_iterations):
        current_iteration = iteration_num + 1
        remaining_iterations = max_iterations - current_iteration
        
        # Add iteration context to the user message
        iteration_context = (
            f"\n\n[Iteration {current_iteration}/{max_iterations} - {remaining_iterations} iterations remaining]"
        )
        
        # Append iteration info to last user message for context
        if messages[-1]["role"] == "user" and "[Iteration" not in messages[-1]["content"]:
            messages[-1]["content"] += iteration_context

        response = client.beta.chat.completions.parse(
            model=llm_model,
            messages=messages,
            tools=tools,
            response_format=ProductSnapshot,
        )

        if response.choices[0].message.tool_calls:
            # Check if we're at max iterations before allowing more tool calls
            if current_iteration == max_iterations:
                logger.info(f"Reached maximum iterations ({max_iterations}). Forcing final response.")
                # Force the model to provide final response by removing tools
                completion = client.beta.chat.completions.parse(
                    model=llm_model,
                    messages=messages,
                    tools=[],  # No tools for final call
                    response_format=ProductSnapshot,
                )
                snapshot = completion.choices[0].message.parsed
                if snapshot:
                    logger.info("Successfully extracted ProductSnapshot (forced at max iterations)")
                    logger.info(f"Final ProductSnapshot: {snapshot.model_dump_json(indent=2)}")
                    emitter.emit_complete()
                    return snapshot
                else:
                    logger.error("Forced response returned None")
                    raise RuntimeError("Failed to extract product snapshot at max iterations")
            
            tool_calls = response.choices[0].message.tool_calls
            logger.info(f"LLM called {len(tool_calls)} tool(s)")

            # Emit reading events for each page
            for tc in tool_calls:
                if tc.function.name in ["fetch_web_content"]:
                    try:
                        args = json.loads(tc.function.arguments)
                        url = args.get("url")
                        if url:
                            emitter.emit_reading(url)
                    except Exception:
                        pass

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
            # No tool calls, we have final response
            snapshot = response.choices[0].message.parsed
            if snapshot:
                logger.info("Successfully extracted ProductSnapshot")
                logger.info(f"Final ProductSnapshot: {snapshot.model_dump_json(indent=2)}")
                emitter.emit_complete()
                return snapshot
            else:
                break
    else:
        # Loop completed without break - should not happen with forced output
        logger.error(f"Failed to generate product snapshot after {max_iterations} iterations")
        emitter.emit_error(f"Failed to extract after {max_iterations} iterations")
        raise RuntimeError(f"Failed to generate product snapshot after {max_iterations} iterations")
    
    # Reached here only if we broke out due to None response
    logger.error(f"Failed to extract after {max_iterations} iterations - parsed response was None")
    emitter.emit_error("Failed to extract product snapshot - parsed response was None")
    raise RuntimeError("Failed to extract product snapshot after {max_iterations} iterations")
