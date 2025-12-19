"""Azure OpenAI client configuration utilities."""
from __future__ import annotations

import os
from typing import Tuple

from dotenv import load_dotenv
from openai import AzureOpenAI

DEFAULT_API_VERSION = "2024-02-01"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing Azure OpenAI configuration: {name}")
    return value


def load_client() -> Tuple[AzureOpenAI, str]:
    """Return a configured Azure OpenAI client and LLM model name."""
    load_dotenv()
    endpoint = _require_env("AZURE_OPENAI_ENDPOINT")
    api_key = _require_env("AZURE_OPENAI_API_KEY")
    deployment = _require_env("AZURE_OPENAI_DEPLOYMENT")
    llm_model = _require_env("LLM_MODEL")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_API_VERSION)

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )
    return client, llm_model
