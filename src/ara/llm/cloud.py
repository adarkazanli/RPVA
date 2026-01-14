"""Cloud LLM integration using Anthropic Claude API.

Provides cloud-based language model capabilities for complex queries.
"""

import os
import re
import time
from dataclasses import dataclass

from .model import LLMResponse

# Try to import anthropic, gracefully handle if not installed
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    anthropic = None
    ANTHROPIC_AVAILABLE = False


@dataclass
class CloudLLMConfig:
    """Configuration for cloud LLM."""

    api_key: str
    model: str = "claude-3-haiku-20240307"
    max_tokens: int = 1024
    temperature: float = 0.7

    @classmethod
    def from_env(cls) -> "CloudLLMConfig":
        """Create config from environment variables.

        Returns:
            CloudLLMConfig with API key from environment.

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Set it to use cloud LLM features."
            )
        return cls(api_key=api_key)


class CloudLanguageModel:
    """Cloud-based language model using Claude API.

    Implements the LanguageModel protocol for cloud inference.
    """

    def __init__(self, config: CloudLLMConfig) -> None:
        """Initialize the cloud language model.

        Args:
            config: Cloud LLM configuration.
        """
        self._config = config
        self._system_prompt: str | None = None

        if ANTHROPIC_AVAILABLE:
            self._client = anthropic.Anthropic(api_key=config.api_key)
        else:
            self._client = None

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._config.model

    def generate(self, prompt: str) -> LLMResponse:
        """Generate a response using the cloud API.

        Args:
            prompt: User prompt.

        Returns:
            LLMResponse with generated text.

        Raises:
            Exception: If API call fails.
        """
        if self._client is None:
            raise RuntimeError("Anthropic SDK not installed. Run: pip install anthropic")

        kwargs = {
            "model": self._config.model,
            "max_tokens": self._config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }

        if self._system_prompt:
            kwargs["system"] = self._system_prompt

        start_time = time.time()
        response = self._client.messages.create(**kwargs)
        latency_ms = int((time.time() - start_time) * 1000)

        text = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens

        return LLMResponse(
            text=text,
            tokens_used=tokens,
            model=self._config.model,
            latency_ms=latency_ms,
        )

    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt.

        Args:
            prompt: System prompt to use.
        """
        self._system_prompt = prompt

    def clear_context(self) -> None:
        """Clear conversation context."""
        self._system_prompt = None


class MockCloudModel:
    """Mock cloud model for testing."""

    def __init__(self) -> None:
        """Initialize mock model."""
        self._response = "Mock cloud response"
        self._system_prompt: str | None = None
        self._calls: list[str] = []

    @property
    def calls(self) -> list[str]:
        """Get list of calls made."""
        return self._calls.copy()

    def set_response(self, response: str) -> None:
        """Set the mock response.

        Args:
            response: Response to return.
        """
        self._response = response

    def generate(self, prompt: str) -> LLMResponse:
        """Generate mock response.

        Args:
            prompt: Input prompt.

        Returns:
            Mock LLMResponse.
        """
        self._calls.append(prompt)
        return LLMResponse(
            text=self._response,
            tokens_used=len(prompt.split()) + len(self._response.split()),
            model="mock-cloud",
            latency_ms=50,  # Mock latency
        )

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt."""
        self._system_prompt = prompt

    def clear_context(self) -> None:
        """Clear context."""
        self._system_prompt = None
        self._calls.clear()


def score_query_complexity(query: str) -> float:
    """Score query complexity for routing decisions.

    Args:
        query: User query string.

    Returns:
        Complexity score from 0.0 (simple) to 1.0 (complex).
    """
    score = 0.0

    # Length factor
    word_count = len(query.split())
    if word_count > 20:
        score += 0.2
    elif word_count > 10:
        score += 0.1

    # Question complexity indicators
    complex_patterns = [
        r"\bexplain\b",
        r"\bdifference between\b",
        r"\bcompare\b",
        r"\bwrite\b.*\bcode\b",
        r"\bimplement\b",
        r"\banalyze\b",
        r"\bsummarize\b",
        r"\blist\s+\d+\b",
        r"\bstep[s]?\s+by\s+step\b",
        r"\bpros?\s+and\s+cons?\b",
    ]

    for pattern in complex_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            score += 0.15

    # Code-related keywords
    code_keywords = [
        "function",
        "algorithm",
        "python",
        "javascript",
        "code",
        "programming",
        "api",
        "database",
        "sql",
    ]

    query_lower = query.lower()
    for keyword in code_keywords:
        if keyword in query_lower:
            score += 0.1
            break

    # Multi-part questions
    if "?" in query and query.count("?") > 1:
        score += 0.1

    # Connectors indicating multi-part reasoning
    connectors = ["and then", "after that", "also", "additionally", "furthermore"]
    for connector in connectors:
        if connector in query_lower:
            score += 0.05

    return min(1.0, score)


def should_use_cloud_fallback(error: Exception) -> bool:
    """Determine if cloud fallback should be triggered.

    Args:
        error: Exception from local LLM.

    Returns:
        True if should fallback to cloud.
    """
    error_msg = str(error).lower()

    # Context overflow
    if "context" in error_msg and ("overflow" in error_msg or "length" in error_msg):
        return True

    return "exceeded" in error_msg


def should_use_cloud_fallback_for_complexity(complexity_score: float) -> bool:
    """Determine if cloud should be used based on complexity.

    Args:
        complexity_score: Query complexity score.

    Returns:
        True if cloud should be used.
    """
    return complexity_score >= 0.7


__all__ = [
    "CloudLanguageModel",
    "CloudLLMConfig",
    "MockCloudModel",
    "score_query_complexity",
    "should_use_cloud_fallback",
    "should_use_cloud_fallback_for_complexity",
]
