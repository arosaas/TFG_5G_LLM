from abc import ABC, abstractmethod
from typing import List, Any
import logging

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_content(self, model: str, contents: Any, config: Any) -> Any:
        """
        Generate content using the LLM.

        Args:
            model: Model name to use
            contents: Input contents for generation
            config: Generation configuration

        Returns:
            Generated response
        """
        pass

    @abstractmethod
    def embed_content(self, model: str, contents: Any) -> Any:
        """
        Generate embeddings for content.

        Args:
            model: Model name to use for embeddings
            contents: Input contents to embed

        Returns:
            Embedding response
        """
        pass

    @abstractmethod
    def create_cached_content(self, model: str, config: Any) -> Any:
        """
        Create cached content (for CAG).

        Args:
            model: Model name to use
            config: Cached content configuration

        Returns:
            Cached content object
        """
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider implementation."""

    def __init__(self, api_key: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        logger.info("Initialized GeminiProvider")

    def generate_content(self, model: str, contents: Any, config: Any) -> Any:
        logger.debug(f"Generating content with Gemini model {model}")
        return self.client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )

    def embed_content(self, model: str, contents: Any) -> Any:
        logger.debug(f"Generating embeddings with Gemini model {model}")
        return self.client.models.embed_content(
            model=model,
            contents=contents
        )

    def create_cached_content(self, model: str, config: Any) -> Any:
        logger.debug(f"Creating cached content with Gemini model {model}")
        return self.client.caches.create(
            model=model,
            config=config
        )


# Future implementations could include:
# class OllamaProvider(LLMProvider):
#     def __init__(self, base_url: str = "http://localhost:11434"):
#         self.base_url = base_url
#         logger.info(f"Initialized OllamaProvider with base_url {base_url}")
#
#     # ... implementations using requests to Ollama API
#
# class OpenAIProvider(LLMProvider):
#     def __init__(self, api_key: str):
#         self.client = openai.OpenAI(api_key=api_key)
#         logger.info("Initialized OpenAIProvider")
#
#     # ... implementations using OpenAI API