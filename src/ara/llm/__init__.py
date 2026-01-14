"""Language model module for Ara Voice Assistant.

Provides LLM inference using Ollama or mock implementation.
"""

from typing import TYPE_CHECKING

from .mock import MockLanguageModel
from .model import LanguageModel, LLMResponse, StreamToken

if TYPE_CHECKING:
    from ..config import LLMConfig


def create_language_model(
    config: "LLMConfig | None" = None,
    use_mock: bool = False,
) -> LanguageModel:
    """Create a language model instance.

    Args:
        config: LLM configuration
        use_mock: If True, return mock implementation for testing

    Returns:
        LanguageModel implementation
    """
    if use_mock:
        return MockLanguageModel()

    # Default config values
    model = "llama3.2:3b"
    host = "http://localhost:11434"
    max_tokens = 150
    temperature = 0.7

    if config is not None:
        model = config.model
        host = config.host
        max_tokens = config.max_tokens
        temperature = config.temperature

    # Try to use Ollama
    try:
        from .ollama import OllamaLanguageModel

        llm = OllamaLanguageModel(
            model=model,
            host=host,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Set system prompt if provided
        if config is not None and config.system_prompt:
            llm.set_system_prompt(config.system_prompt)

        return llm
    except RuntimeError:
        # Fall back to mock if Ollama not available
        import logging

        logging.getLogger(__name__).warning("Ollama not available, using mock language model")
        return MockLanguageModel()


__all__ = [
    "LLMResponse",
    "LanguageModel",
    "MockLanguageModel",
    "StreamToken",
    "create_language_model",
]
