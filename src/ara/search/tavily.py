"""Tavily search integration for real-time web search.

Provides web search capabilities using the Tavily API,
optimized for AI assistants with clean, summarized results.
"""

import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _find_and_load_env() -> bool:
    """Find and load .env file from project root.

    Tries multiple strategies to locate the .env file:
    1. Relative to this module (src/ara/search/tavily.py -> project root)
    2. Current working directory
    3. Parent directories up to 5 levels

    Returns:
        True if .env was loaded, False otherwise.
    """
    try:
        from pathlib import Path

        from dotenv import load_dotenv
    except ImportError:
        logger.debug("python-dotenv not installed, skipping .env loading")
        return False

    # Strategy 1: Relative to this module file
    # tavily.py is at src/ara/search/tavily.py, so project root is 4 levels up
    module_path = Path(__file__).resolve()
    project_root = module_path.parent.parent.parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        load_dotenv(env_file)
        logger.debug(f"Loaded .env from module-relative path: {env_file}")
        return True

    # Strategy 2: Current working directory
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        load_dotenv(cwd_env)
        logger.debug(f"Loaded .env from cwd: {cwd_env}")
        return True

    # Strategy 3: Walk up parent directories (for when run from subdirectory)
    current = Path.cwd()
    for _ in range(5):
        parent_env = current / ".env"
        if parent_env.exists():
            load_dotenv(parent_env)
            logger.debug(f"Loaded .env from parent: {parent_env}")
            return True
        if current.parent == current:
            break
        current = current.parent

    # Strategy 4: Just try load_dotenv() default behavior
    load_dotenv()
    logger.debug("Tried default load_dotenv()")
    return False


# Load environment variables at module import
_find_and_load_env()

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
        max_retries: int = 2,
        retry_delay: float = 0.5,
    ) -> SearchResult:
        """Perform a web search with retry logic.

        Args:
            query: The search query
            max_results: Maximum number of results to return (default 5)
            search_depth: "basic" or "advanced" (advanced is slower but better)
            include_answer: Whether to include a direct answer
            max_retries: Maximum number of retry attempts (default 2)
            retry_delay: Delay between retries in seconds (default 0.5)

        Returns:
            SearchResult with answer and/or search results
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for query: '{query}'")
                    time.sleep(retry_delay * attempt)  # Exponential backoff

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
                last_error = e
                error_str = str(e).lower()

                # Don't retry on certain errors
                if "invalid api key" in error_str or "unauthorized" in error_str:
                    logger.error(f"Search failed (auth error, not retrying): {e}")
                    break

                if attempt < max_retries:
                    logger.warning(f"Search attempt {attempt + 1} failed: {e}")
                else:
                    logger.error(f"Search failed after {max_retries + 1} attempts: {e}")

        return SearchResult(
            query=query,
            answer=None,
            results=[],
            success=False,
            error=str(last_error) if last_error else "Unknown error",
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
    import os

    tavily_key = os.environ.get("TAVILY_API_KEY")
    key_preview = f"{tavily_key[:8]}..." if tavily_key and len(tavily_key) > 8 else None

    logger.info(f"Creating search client (use_mock={use_mock})")
    logger.info(f"TAVILY_API_KEY: {'set (' + key_preview + ')' if key_preview else 'NOT SET'}")
    logger.info(f"TAVILY_AVAILABLE: {TAVILY_AVAILABLE}")

    if use_mock:
        logger.info("Using mock search client (explicitly requested)")
        return MockTavilySearch(api_key=api_key)

    if not TAVILY_AVAILABLE:
        logger.warning("tavily-python not installed, using mock client")
        return MockTavilySearch(api_key=api_key)

    if not tavily_key and not api_key:
        logger.warning("No TAVILY_API_KEY found in environment, using mock client")
        logger.warning("Set TAVILY_API_KEY in .env or environment to enable web search")
        return MockTavilySearch(api_key=api_key)

    try:
        client = TavilySearch(api_key=api_key)
        logger.info("Created real TavilySearch client successfully")
        return client
    except RuntimeError as e:
        logger.error(f"Failed to create Tavily client: {e}")
        logger.warning("Falling back to mock search client")
        return MockTavilySearch(api_key=api_key)


__all__ = ["SearchResult", "TavilySearch", "MockTavilySearch", "create_search_client"]
