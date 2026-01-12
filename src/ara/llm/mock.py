"""Mock language model for testing.

Provides a controllable mock implementation for unit and integration testing.
"""

import time
from collections.abc import Iterator

from .model import LLMResponse, StreamToken


class MockLanguageModel:
    """Mock language model for testing.

    Allows setting predetermined responses for predictable testing.
    """

    def __init__(self) -> None:
        """Initialize mock language model."""
        self._system_prompt: str = ""
        self._response_text: str = "This is a mock response."
        self._call_count: int = 0
        self._context: list[dict[str, str]] = []
        self._error_message: str | None = None
        self._latency_ms: int = 100  # Simulated latency

    def set_response(self, text: str) -> None:
        """Set the response to return on next generation.

        Args:
            text: Text to return
        """
        self._response_text = text
        self._error_message = None

    def set_error(self, message: str) -> None:
        """Set an error to raise on next generation.

        Args:
            message: Error message
        """
        self._error_message = message

    def set_latency(self, latency_ms: int) -> None:
        """Set simulated latency.

        Args:
            latency_ms: Latency in milliseconds
        """
        self._latency_ms = latency_ms

    def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Return preset response."""
        self._call_count += 1

        if self._error_message:
            raise RuntimeError(self._error_message)

        # Add to context
        self._context.append({"role": "user", "content": prompt})
        self._context.append({"role": "assistant", "content": self._response_text})

        # Simulate latency
        time.sleep(self._latency_ms / 1000)

        # Estimate tokens
        tokens_used = len(self._response_text.split()) + len(prompt.split())

        return LLMResponse(
            text=self._response_text,
            tokens_used=tokens_used,
            model="mock-model",
            latency_ms=self._latency_ms,
        )

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> Iterator[StreamToken]:
        """Stream mock response token by token."""
        self._call_count += 1

        if self._error_message:
            raise RuntimeError(self._error_message)

        # Add to context
        self._context.append({"role": "user", "content": prompt})
        self._context.append({"role": "assistant", "content": self._response_text})

        # Yield response word by word
        words = self._response_text.split()
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            yield StreamToken(
                token=word + ("" if is_last else " "),
                is_complete=is_last,
            )
            time.sleep(0.01)  # Small delay between tokens

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self._system_prompt = prompt

    def clear_context(self) -> None:
        """Clear conversation context."""
        self._context.clear()

    @property
    def system_prompt(self) -> str:
        """Get current system prompt."""
        return self._system_prompt

    @property
    def call_count(self) -> int:
        """Get number of generate calls."""
        return self._call_count

    @property
    def context_length(self) -> int:
        """Get current context length."""
        return len(self._context)

    @property
    def context(self) -> list[dict[str, str]]:
        """Get conversation context."""
        return self._context.copy()

    def clear(self) -> None:
        """Reset mock state."""
        self._response_text = "This is a mock response."
        self._call_count = 0
        self._context.clear()
        self._error_message = None


__all__ = ["MockLanguageModel"]
