"""Language model protocol and data classes.

Defines the interface for language model inference.
"""

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class LLMResponse:
    """Response from language model.

    Attributes:
        text: Generated response text
        tokens_used: Number of tokens consumed
        model: Model identifier
        latency_ms: Response latency in milliseconds
    """

    text: str
    tokens_used: int
    model: str
    latency_ms: int


@dataclass
class StreamToken:
    """Single token in streaming response.

    Attributes:
        token: Token text
        is_complete: True if this is the final token
    """

    token: str
    is_complete: bool


class LanguageModel(Protocol):
    """Interface for language model inference.

    Implementations generate text responses from prompts.
    """

    def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate response for prompt.

        Args:
            prompt: User input text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)

        Returns:
            LLMResponse with generated text

        Raises:
            RuntimeError: If generation fails
        """
        ...

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> Iterator[StreamToken]:
        """Stream response tokens as they're generated.

        Args:
            prompt: User input text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            StreamToken for each generated token
        """
        ...

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt for conversation context.

        Args:
            prompt: System prompt text
        """
        ...

    def clear_context(self) -> None:
        """Clear conversation history."""
        ...


__all__ = ["LLMResponse", "LanguageModel", "StreamToken"]
