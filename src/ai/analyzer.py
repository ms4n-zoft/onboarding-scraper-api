"""LLM-based analysis for structured product data extraction."""
from __future__ import annotations

from openai import AzureOpenAI

from ..schemas.product import ProductSnapshot

PRODUCT_ANALYSIS_SYSTEM_PROMPT = (
    "You are a product intelligence assistant generating data for a catalog. "
    "Always populate the ProductSnapshot schema exactly, using only evidence from the page "
    "content provided. Write in a neutral, professional tone, keep numeric values as numbers, "
    "and ensure every URL is an https link. If information is unavailable, return nulls "
    "or empty lists as appropriate."
)


def extract_product_snapshot(
    client: AzureOpenAI,
    llm_model: str,
    url: str,
    page_text: str,
) -> ProductSnapshot:
    """Extract structured product data from page content using Azure OpenAI.
    
    Args:
        client: Configured Azure OpenAI client
        llm_model: LLM model name
        url: Source URL of the content
        page_text: Cleaned text content from webpage
        
    Returns:
        ProductSnapshot with extracted product intelligence
    """
    user_prompt = (
        "Use the webpage content to complete the ProductSnapshot schema. "
        "Stay faithful to verified details, prefer official data, and do not fabricate. "
        "If a field is unknown, return null."
        f"\n\nURL: {url}\n\nWebpage content:\n{page_text}"
    )
    completion = client.beta.chat.completions.parse(
        model=llm_model,
        messages=[
            {"role": "system", "content": PRODUCT_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format=ProductSnapshot,
    )
    return completion.choices[0].message.parsed
