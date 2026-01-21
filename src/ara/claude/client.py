"""Claude API client for Ara Voice Assistant.

Provides integration with Claude API for voice queries.
"""

import os
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anthropic

from ara.claude.errors import (
    ClaudeAPIError,
    ClaudeAuthError,
    ClaudeConnectivityError,
    ClaudeTimeoutError,
)

if TYPE_CHECKING:
    from ara.claude.session import ClaudeSession


# System prompt for concise voice responses (~150 words)
SYSTEM_PROMPT = """You are Claude, an AI assistant being accessed through a voice interface called Ara.

IMPORTANT GUIDELINES:
- Keep responses concise and spoken-word friendly (aim for ~150 words or less)
- Avoid bullet points, numbered lists, or formatting that doesn't translate well to speech
- Use natural conversational language
- If a topic requires a longer explanation, provide a brief summary and offer to elaborate
- When summarizing, focus on the most important points
- Avoid using URLs, code blocks, or special characters

The user is speaking to you through voice, and your response will be read aloud."""


@dataclass
class ClaudeClientConfig:
    """Configuration for Claude client."""

    api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 500
    temperature: float = 0.7
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "ClaudeClientConfig":
        """Create config from environment variables.

        Returns:
            ClaudeClientConfig with API key from environment.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Set it to use Claude query features."
            )
        return cls(api_key=api_key)


@dataclass
class ClaudeResponse:
    """Response from Claude API."""

    text: str
    tokens_used: int
    model: str
    latency_ms: int


class ClaudeClient:
    """Client for Claude API communication."""

    def __init__(self, config: ClaudeClientConfig) -> None:
        """Initialize Claude client.

        Args:
            config: Configuration for the client.
        """
        self._config = config
        self._client = anthropic.Anthropic(
            api_key=config.api_key,
            timeout=config.timeout_seconds,
        )

    def check_connectivity(self) -> bool:
        """Check if we can reach the Claude API.

        Returns:
            True if connectivity is available, False otherwise.

        Raises:
            ClaudeConnectivityError: If connectivity check fails with details.
        """
        try:
            # Try to resolve Anthropic's API endpoint
            socket.create_connection(("api.anthropic.com", 443), timeout=5)
            return True
        except (TimeoutError, socket.gaierror, OSError) as e:
            raise ClaudeConnectivityError(
                f"Cannot reach Claude API: {e}. Please check your internet connection."
            ) from e

    def send_message(
        self,
        query: str,
        session: "ClaudeSession | None" = None,
    ) -> ClaudeResponse:
        """Send a message to Claude and get a response.

        Args:
            query: The user's query text.
            session: Optional session for conversation context.

        Returns:
            ClaudeResponse with text and metadata.

        Raises:
            ClaudeTimeoutError: If the request times out.
            ClaudeAPIError: If the API returns an error.
            ClaudeAuthError: If authentication fails.
            ClaudeConnectivityError: If network is unavailable.
        """
        import time

        start_time = time.time()

        # Build messages list
        messages = []
        if session:
            messages = session.get_api_messages()

        # Add current query
        messages.append({"role": "user", "content": query})

        try:
            response = self._client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                system=SYSTEM_PROMPT,
                messages=messages,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response text
            text = ""
            if response.content:
                text = response.content[0].text

            return ClaudeResponse(
                text=text,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens,
                model=response.model,
                latency_ms=latency_ms,
            )

        except anthropic.AuthenticationError as e:
            raise ClaudeAuthError(
                "Invalid API key. Please check your ANTHROPIC_API_KEY."
            ) from e
        except anthropic.APITimeoutError as e:
            # Catch timeout BEFORE connection error (timeout may be a subclass)
            raise ClaudeTimeoutError(
                f"Request timed out after {self._config.timeout_seconds} seconds."
            ) from e
        except anthropic.APIConnectionError as e:
            raise ClaudeConnectivityError(
                f"Failed to connect to Claude API: {e}"
            ) from e
        except anthropic.APIStatusError as e:
            raise ClaudeAPIError(
                f"API error: {e.message}",
                status_code=e.status_code,
            ) from e


__all__ = [
    "ClaudeClient",
    "ClaudeClientConfig",
    "ClaudeResponse",
    "SYSTEM_PROMPT",
]
