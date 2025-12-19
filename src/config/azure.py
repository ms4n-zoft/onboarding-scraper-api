"""Azure OpenAI client configuration utilities."""
from __future__ import annotations

import os
from typing import Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI

from ..utils import get_required_env_var

DEFAULT_API_VERSION = "2024-02-01"


def load_azure_openai_client() -> Tuple[AzureOpenAI, str]:
    """Load and return a configured Azure OpenAI client with LLM model name.
    
    Returns:
        Tuple of (AzureOpenAI client, LLM model name)
        
    Raises:
        RuntimeError: If required environment variables are missing.
    """
    load_dotenv()
    endpoint = get_required_env_var("AZURE_OPENAI_ENDPOINT")
    api_key = get_required_env_var("AZURE_OPENAI_API_KEY")
    deployment = get_required_env_var("AZURE_OPENAI_DEPLOYMENT")
    llm_model = get_required_env_var("LLM_MODEL")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    return client, llm_model
