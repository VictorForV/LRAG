"""Model providers for Semantic Search Agent."""

from typing import Optional, Any
import httpx
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModel
from src.settings import load_settings
import logging

logger = logging.getLogger(__name__)


def get_llm_model(
    model_choice: Optional[str] = None,
    user_settings: Optional[Any] = None
) -> OpenAIModel:
    """
    Get LLM model configuration based on user settings or environment variables.
    Supports any OpenAI-compatible API provider.

    Args:
        model_choice: Optional override for model choice
        user_settings: Optional user-specific settings with API keys and proxy

    Returns:
        Configured OpenAI-compatible model
    """
    settings = load_settings()

    # Build proxy configuration if user has proxy settings
    http_client = None
    if user_settings and user_settings.get("http_proxy_host"):
        proxy_host = user_settings["http_proxy_host"]
        proxy_port = user_settings["http_proxy_port"]
        proxy_username = user_settings.get("http_proxy_username")
        proxy_password = user_settings.get("http_proxy_password")

        # Build proxy URL
        if proxy_username and proxy_password:
            proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"
        else:
            proxy_url = f"http://{proxy_host}:{proxy_port}"

        logger.info(f"LLM using proxy: {proxy_host}:{proxy_port}")
        http_client = httpx.AsyncClient(proxy=proxy_url, timeout=60.0)

    # Use user settings if available, otherwise fall back to global settings
    llm_choice = model_choice
    if not llm_choice:
        llm_choice = (user_settings.get("llm_model") or settings.llm_model) if user_settings else settings.llm_model

    api_key = (user_settings.get("llm_api_key") or settings.llm_api_key) if user_settings else settings.llm_api_key
    base_url = (user_settings.get("llm_base_url") or settings.llm_base_url) if user_settings else settings.llm_base_url

    # Create provider based on configuration
    provider = OpenAIProvider(base_url=base_url, api_key=api_key, http_client=http_client)

    return OpenAIModel(llm_choice, provider=provider)


def get_embedding_model() -> OpenAIModel:
    """
    Get embedding model configuration.
    Uses OpenAI embeddings API (or compatible provider).

    Returns:
        Configured embedding model
    """
    settings = load_settings()

    # For embeddings, use the same provider configuration
    provider = OpenAIProvider(
        base_url=settings.llm_base_url, api_key=settings.llm_api_key
    )

    return OpenAIModel(settings.embedding_model, provider=provider)


def get_model_info() -> dict:
    """
    Get information about current model configuration.

    Returns:
        Dictionary with model configuration info
    """
    settings = load_settings()

    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_base_url": settings.llm_base_url,
        "embedding_model": settings.embedding_model,
    }


def validate_llm_configuration() -> bool:
    """
    Validate that LLM configuration is properly set.

    Returns:
        True if configuration is valid
    """
    try:
        # Check if we can create a model instance
        get_llm_model()
        return True
    except Exception as e:
        print(f"LLM configuration validation failed: {e}")
        return False
