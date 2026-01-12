"""Web search functionality using DuckDuckGo.

Provides search capabilities and result summarization for the voice assistant.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .model import LanguageModel

# Try to import duckduckgo_search, gracefully handle if not installed
try:
    from duckduckgo_search import DDGS

    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    DDGS = None


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }


@dataclass
class SearchResponse:
    """Complete search response with results and summary."""

    query: str
    results: list[SearchResult]
    summary: str


class WebSearcher:
    """Web search using DuckDuckGo.

    Performs searches and formats results for LLM consumption.
    """

    def __init__(self, max_results: int = 5, timeout: int = 10) -> None:
        """Initialize the web searcher.

        Args:
            max_results: Maximum number of results to return.
            timeout: Request timeout in seconds.
        """
        self._max_results = max_results
        self._timeout = timeout

    @property
    def max_results(self) -> int:
        """Get maximum results."""
        return self._max_results

    def search(self, query: str) -> list[SearchResult]:
        """Perform a web search.

        Args:
            query: Search query string.

        Returns:
            List of search results.
        """
        if not DDGS_AVAILABLE:
            return []

        try:
            with DDGS() as ddgs:
                raw_results = ddgs.text(
                    query,
                    max_results=self._max_results,
                )

                results = []
                for item in raw_results:
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("href", ""),
                            snippet=item.get("body", ""),
                        )
                    )

                return results

        except Exception:
            return []

    def format_results_for_llm(self, results: list[SearchResult]) -> str:
        """Format search results for LLM context.

        Args:
            results: List of search results.

        Returns:
            Formatted string suitable for LLM context.
        """
        if not results:
            return "No search results found."

        lines = ["Web search results:"]
        for i, result in enumerate(results, 1):
            lines.append(f"\n{i}. {result.title}")
            lines.append(f"   URL: {result.url}")
            lines.append(f"   {result.snippet}")

        return "\n".join(lines)


class SearchSummarizer:
    """Summarizes search results using an LLM."""

    SUMMARY_PROMPT = """Based on the following web search results, provide a concise and helpful answer to the user's question. If the search results don't contain relevant information, say so.

User's question: {query}

{results}

Provide a helpful, conversational response:"""

    NO_RESULTS_RESPONSE = (
        "I couldn't find any relevant results for that search. "
        "Would you like to try a different query?"
    )

    def __init__(self, llm: "LanguageModel") -> None:
        """Initialize the summarizer.

        Args:
            llm: Language model for summarization.
        """
        self._llm = llm
        self._searcher = WebSearcher()

    def summarize(self, query: str, results: list[SearchResult]) -> str:
        """Summarize search results into a response.

        Args:
            query: Original user query.
            results: Search results to summarize.

        Returns:
            Summarized response string.
        """
        if not results:
            return self.NO_RESULTS_RESPONSE

        formatted = self._searcher.format_results_for_llm(results)
        prompt = self.SUMMARY_PROMPT.format(query=query, results=formatted)

        response = self._llm.generate(prompt)
        return response.text

    def search_and_summarize(self, query: str) -> SearchResponse:
        """Perform search and summarize results.

        Args:
            query: Search query.

        Returns:
            SearchResponse with results and summary.
        """
        results = self._searcher.search(query)
        summary = self.summarize(query, results)

        return SearchResponse(
            query=query,
            results=results,
            summary=summary,
        )


__all__ = [
    "SearchResponse",
    "SearchResult",
    "SearchSummarizer",
    "WebSearcher",
]
