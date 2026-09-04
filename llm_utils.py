"""
LLM Utility functions for creating and managing LLM providers.
"""

import logging
from typing import Optional
from llm_providers.base import LLMProvider, GeminiProvider
import configuraciones

logger = logging.getLogger(__name__)

def get_llm_provider() -> LLMProvider:
    """
    Factory function to get the configured LLM provider.

    Returns:
        LLMProvider instance based on configuration
    """
    provider_name = configuraciones.LLM_PROVIDER.lower()

    if provider_name == "gemini":
        if not configuraciones.API_KEY:
            raise ValueError("API_KEY is required for Gemini provider")
        logger.info("Creating Gemini LLM provider")
        return GeminiProvider(configuraciones.API_KEY)

    # Future providers can be added here:
    # elif provider_name == "ollama":
    #     return OllamaProvider(base_url=configuraciones.OLLAMA_BASE_URL)
    # elif provider_name == "openai":
    #     return OpenAIProvider(api_key=configuraciones.API_KEY)
    else:
        logger.warning(f"Unknown LLM provider '{provider_name}', falling back to Gemini")
        if not configuraciones.API_KEY:
            raise ValueError("API_KEY is required for Gemini provider")
        return GeminiProvider(configuraciones.API_KEY)


def get_model_name(model_type: str) -> str:
    """
    Get the model name for the specified type.

    Args:
        model_type: Either "gen" for generation or "emb" for embeddings

    Returns:
        Model name string
    """
    if model_type == "gen":
        return configuraciones.MODEL_GEN
    elif model_type == "emb":
        return configuraciones.MODEL_EMB
    else:
        raise ValueError(f"Unknown model type: {model_type}")