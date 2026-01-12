"""Ollama language model implementation.

Uses Ollama for local LLM inference with models like Llama 3.2.
"""

import logging
import time
from collections.abc import Iterator

from .model import LLMResponse, StreamToken

# Ollama import with fallback
try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ollama = None  # type: ignore

logger = logging.getLogger(__name__)


class OllamaLanguageModel:
    """Language model using Ollama for local inference.

    Ollama provides efficient local LLM inference with support for
    various models like Llama 3.2, Mistral, etc.
    """

    def __init__(
        self,
        model: str = "llama3.2:3b",
        host: str = "http://localhost:11434",
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> None:
        """Initialize Ollama language model.

        Args:
            model: Ollama model name
            host: Ollama server URL
            max_tokens: Default maximum tokens to generate
            temperature: Default sampling temperature

        Raises:
            RuntimeError: If Ollama client is not available
        """
        if not OLLAMA_AVAILABLE:
            raise RuntimeError(
                "Ollama client not available. Install with: pip install ollama"
            )

        self._model = model
        self._host = host
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._system_prompt: str = ""
        self._context: list[dict[str, str]] = []

        # Create client
        self._client = ollama.Client(host=host)

        logger.info(f"Ollama initialized with model: {model} at {host}")

    def _build_messages(self, prompt: str) -> list[dict[str, str]]:
        """Build message list for Ollama API."""
        messages = []

        # Add system prompt if set
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})

        # Add conversation context
        messages.extend(self._context)

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return messages

    def generate(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        """Generate response for prompt.

        Args:
            prompt: User input text
            max_tokens: Maximum tokens (uses default if None)
            temperature: Sampling temperature (uses default if None)

        Returns:
            LLMResponse with generated text
        """
        max_tokens = max_tokens or self._max_tokens
        temperature = temperature if temperature is not None else self._temperature

        messages = self._build_messages(prompt)

        start_time = time.time()

        try:
            response = self._client.chat(
                model=self._model,
                messages=messages,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            )
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}") from e

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract response
        response_text = response["message"]["content"]

        # Update context
        self._context.append({"role": "user", "content": prompt})
        self._context.append({"role": "assistant", "content": response_text})

        # Estimate tokens
        tokens_used = response.get("eval_count", len(response_text.split()))

        logger.debug(
            f"Generated {tokens_used} tokens in {latency_ms}ms: '{response_text[:50]}...'"
        )

        return LLMResponse(
            text=response_text,
            tokens_used=tokens_used,
            model=self._model,
            latency_ms=latency_ms,
        )

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[StreamToken]:
        """Stream response tokens.

        Args:
            prompt: User input text
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Yields:
            StreamToken for each generated token
        """
        max_tokens = max_tokens or self._max_tokens
        temperature = temperature if temperature is not None else self._temperature

        messages = self._build_messages(prompt)

        try:
            stream = self._client.chat(
                model=self._model,
                messages=messages,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
                stream=True,
            )

            full_response = ""
            for chunk in stream:
                token = chunk["message"]["content"]
                full_response += token
                is_complete = chunk.get("done", False)

                yield StreamToken(token=token, is_complete=is_complete)

            # Update context with full response
            self._context.append({"role": "user", "content": prompt})
            self._context.append({"role": "assistant", "content": full_response})

        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            raise RuntimeError(f"LLM streaming failed: {e}") from e

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self._system_prompt = prompt
        logger.debug(f"System prompt set: {prompt[:50]}...")

    def clear_context(self) -> None:
        """Clear conversation history."""
        self._context.clear()
        logger.debug("Conversation context cleared")

    @property
    def model(self) -> str:
        """Get model name."""
        return self._model

    @property
    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            self._client.list()
            return True
        except Exception:
            return False


__all__ = ["OllamaLanguageModel"]
