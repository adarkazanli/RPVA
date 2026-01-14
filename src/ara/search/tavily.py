"""Tavily search integration for real-time web search.

Provides web search capabilities using the Tavily API,
optimized for AI assistants with clean, summarized results.
"""

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Tavily import with fallback
try:
    from tavily import TavilyClient

    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

    class TavilyClient:  # type: ignore[no-redef]
        """Stub for when tavily-python is not installed."""

        pass


@dataclass
class SearchResult:
    """Result from a web search.

    Attributes:
        query: The original search query
        answer: Direct answer to the query (if available)
        results: List of search result summaries
        success: Whether the search was successful
        error: Error message if search failed
    """

    query: str
    answer: str | None
    results: list[dict[str, str]]
    success: bool
    error: str | None = None


class TavilySearch:
    """Web search using Tavily API.

    Tavily is optimized for AI agents, providing clean summaries
    and direct answers to questions.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Tavily search client.

        Args:
            api_key: Tavily API key. If not provided, will look for
                    TAVILY_API_KEY environment variable.

        Raises:
            RuntimeError: If Tavily is not available or no API key provided.
        """
        if not TAVILY_AVAILABLE:
            raise RuntimeError("Tavily not available. Install with: pip install tavily-python")

        self._api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self._api_key:
            raise RuntimeError(
                "Tavily API key required. Set TAVILY_API_KEY env var "
                "or pass api_key to constructor. Get a free key at "
                "https://app.tavily.com/"
            )

        self._client = TavilyClient(api_key=self._api_key)
        logger.info("Tavily search client initialized")

    def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True,
    ) -> SearchResult:
        """Perform a web search.

        Args:
            query: The search query
            max_results: Maximum number of results to return (default 5)
            search_depth: "basic" or "advanced" (advanced is slower but better)
            include_answer: Whether to include a direct answer

        Returns:
            SearchResult with answer and/or search results
        """
        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=include_answer,
            )

            # Extract results
            results = []
            for r in response.get("results", []):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "content": r.get("content", ""),
                    }
                )

            answer = response.get("answer") if include_answer else None

            logger.info(f"Search completed: {len(results)} results for '{query}'")

            return SearchResult(
                query=query,
                answer=answer,
                results=results,
                success=True,
            )

        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return SearchResult(
                query=query,
                answer=None,
                results=[],
                success=False,
                error=str(e),
            )

    def quick_answer(self, query: str) -> str | None:
        """Get a quick answer to a question.

        Uses Tavily's QnA search for concise answers.

        Args:
            query: The question to answer

        Returns:
            Answer string or None if no answer found
        """
        try:
            answer: str = self._client.qna_search(query=query)
            logger.info(f"Quick answer for '{query}': {answer[:50]}...")
            return answer
        except Exception as e:
            logger.error(f"Quick answer failed for '{query}': {e}")
            return None


class MockTavilySearch:
    """Mock search client for testing."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize mock search client."""
        self._api_key = api_key or "mock-api-key"

    def search(
        self,
        query: str,
        max_results: int = 5,  # noqa: ARG002
        search_depth: str = "basic",  # noqa: ARG002
        include_answer: bool = True,  # noqa: ARG002
    ) -> SearchResult:
        """Return mock search results."""
        return SearchResult(
            query=query,
            answer=f"This is a mock answer for: {query}",
            results=[
                {
                    "title": f"Mock Result 1 for {query}",
                    "url": "https://example.com/1",
                    "content": f"Mock content about {query}",
                },
                {
                    "title": f"Mock Result 2 for {query}",
                    "url": "https://example.com/2",
                    "content": f"More mock content about {query}",
                },
            ],
            success=True,
        )

    def quick_answer(self, query: str) -> str | None:
        """Return mock quick answer."""
        return f"Mock answer: {query}"


def create_search_client(
    api_key: str | None = None,
    use_mock: bool = False,
) -> TavilySearch | MockTavilySearch:
    """Create a search client.

    Args:
        api_key: Tavily API key (optional, uses env var if not provided)
        use_mock: If True, return mock client for testing

    Returns:
        Search client instance
    """
    if use_mock:
        return MockTavilySearch(api_key=api_key)

    try:
        return TavilySearch(api_key=api_key)
    except RuntimeError as e:
        logger.warning(f"Could not create Tavily client: {e}")
        logger.warning("Falling back to mock search client")
        return MockTavilySearch(api_key=api_key)


__all__ = ["SearchResult", "TavilySearch", "MockTavilySearch", "create_search_client"]
