"""Perplexity search integration for AI-powered web search.

Provides web search capabilities using the Perplexity API,
which combines web search with AI reasoning for comprehensive answers.
"""

import logging
import os
import re
import time
from pathlib import Path

import httpx

from .tavily import SearchResult

logger = logging.getLogger(__name__)


def _load_env() -> None:
    """Load .env file if available."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    # Try module-relative path first (src/ara/search/perplexity.py -> project root)
    module_path = Path(__file__).resolve()
    project_root = module_path.parent.parent.parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        load_dotenv(env_file)
        logger.debug(f"Loaded .env from: {env_file}")


# Load environment variables at module import
_load_env()

# Perplexity API configuration
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"  # Options: sonar, sonar-pro, sonar-reasoning
PERPLEXITY_TIMEOUT = 30.0  # seconds


class PerplexitySearch:
    """Web search using Perplexity API.

    Perplexity provides AI-powered search that combines web results
    with reasoning to provide comprehensive answers.

    API docs: https://docs.perplexity.ai/api-reference/chat-completions-post
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = PERPLEXITY_MODEL,
        timeout: float = PERPLEXITY_TIMEOUT,
    ) -> None:
        """Initialize Perplexity search client.

        Args:
            api_key: Perplexity API key. If not provided, will look for
                    PERPLEXITY_API_KEY environment variable.
            model: Model to use (sonar, sonar-pro, sonar-reasoning).
            timeout: Request timeout in seconds.
        """
        self._api_key = api_key or os.environ.get("PERPLEXITY_API_KEY")
        self._model = model
        self._timeout = timeout

        if self._api_key:
            logger.info(f"Perplexity search client initialized (model: {model})")
        else:
            logger.warning(
                "PERPLEXITY_API_KEY not set - Perplexity search unavailable. "
                "Get an API key at https://www.perplexity.ai/"
            )

    @property
    def is_available(self) -> bool:
        """Check if Perplexity search is available.

        Returns:
            True if API key is configured, False otherwise.
        """
        return bool(self._api_key)

    def search(
        self,
        query: str,
        max_results: int = 5,  # noqa: ARG002 - Perplexity handles result count internally
        max_retries: int = 2,
        retry_delay: float = 0.5,
    ) -> SearchResult:
        """Perform a Perplexity search.

        Args:
            query: The search query
            max_results: Not used by Perplexity (kept for API compatibility)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds

        Returns:
            SearchResult with answer and citations
        """
        if not self._api_key:
            return SearchResult(
                query=query,
                answer=None,
                results=[],
                success=False,
                error="Perplexity API key not configured",
            )

        last_error = None
        start_time = time.time()

        for attempt in range(max_retries + 1):
            try:
                response = self._make_request(query)
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.info(f"Perplexity search completed in {elapsed_ms}ms")
                return response

            except httpx.TimeoutException as e:
                last_error = f"Request timed out: {e}"
                logger.warning(f"Perplexity timeout (attempt {attempt + 1}): {e}")

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP error {e.response.status_code}: {e.response.text}"
                logger.warning(f"Perplexity HTTP error: {last_error}")
                # Don't retry on auth errors
                if e.response.status_code in (401, 403):
                    break

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Perplexity error (attempt {attempt + 1}): {e}")

            if attempt < max_retries:
                time.sleep(retry_delay * (attempt + 1))

        return SearchResult(
            query=query,
            answer=None,
            results=[],
            success=False,
            error=last_error or "Unknown error",
        )

    def _make_request(self, query: str) -> SearchResult:
        """Make the actual API request to Perplexity.

        Args:
            query: The search query

        Returns:
            SearchResult with answer and citations
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful search assistant. Provide concise, accurate answers "
                        "based on current web search results. Keep responses brief but informative, "
                        "suitable for a voice assistant (1-3 sentences for simple queries)."
                    ),
                },
                {"role": "user", "content": query},
            ],
            "temperature": 0.2,  # Low temperature for factual responses
            "max_tokens": 300,  # Keep responses concise for voice
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                PERPLEXITY_API_URL,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

        data = response.json()

        # Extract the answer from the response
        answer = None
        citations = []

        if "choices" in data and len(data["choices"]) > 0:
            message = data["choices"][0].get("message", {})
            raw_answer = message.get("content", "").strip()
            # Remove citation markers like [1], [2][3] for cleaner voice output
            answer = re.sub(r"\[\d+\]", "", raw_answer).strip()
            # Clean up multiple spaces that may result
            answer = re.sub(r"\s+", " ", answer)

        # Extract citations if available (Perplexity returns URLs as strings)
        if "citations" in data and data["citations"]:
            for i, citation in enumerate(data["citations"][:5], 1):
                # Citations are URL strings, not dicts
                if isinstance(citation, str):
                    citations.append({
                        "title": f"Source {i}",
                        "url": citation,
                        "snippet": "",
                    })
                elif isinstance(citation, dict):
                    citations.append({
                        "title": citation.get("title", f"Source {i}"),
                        "url": citation.get("url", ""),
                        "snippet": citation.get("snippet", ""),
                    })

        return SearchResult(
            query=query,
            answer=answer,
            results=citations,
            success=bool(answer),
            error=None if answer else "No answer generated",
        )


def create_perplexity_search(api_key: str | None = None) -> PerplexitySearch | None:
    """Create a Perplexity search client if API key is available.

    Args:
        api_key: Optional API key override

    Returns:
        PerplexitySearch instance if API key available, None otherwise
    """
    client = PerplexitySearch(api_key=api_key)
    if client.is_available:
        return client
    return None


__all__ = [
    "PerplexitySearch",
    "create_perplexity_search",
]
