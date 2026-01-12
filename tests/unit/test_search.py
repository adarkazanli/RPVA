"""Unit tests for web search functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSearchResult:
    """Tests for SearchResult data class."""

    def test_create_search_result(self) -> None:
        """Test creating a SearchResult."""
        from ara.llm.search import SearchResult

        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet text",
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet text"

    def test_search_result_to_dict(self) -> None:
        """Test SearchResult serialization."""
        from ara.llm.search import SearchResult

        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
        )

        data = result.to_dict()
        assert data["title"] == "Test"
        assert data["url"] == "https://example.com"
        assert data["snippet"] == "Snippet"


class TestSearchResponse:
    """Tests for SearchResponse data class."""

    def test_create_search_response(self) -> None:
        """Test creating a SearchResponse."""
        from ara.llm.search import SearchResponse, SearchResult

        results = [
            SearchResult("Title 1", "https://example1.com", "Snippet 1"),
            SearchResult("Title 2", "https://example2.com", "Snippet 2"),
        ]

        response = SearchResponse(
            query="test query",
            results=results,
            summary="Summary of results",
        )

        assert response.query == "test query"
        assert len(response.results) == 2
        assert response.summary == "Summary of results"

    def test_search_response_empty_results(self) -> None:
        """Test SearchResponse with no results."""
        from ara.llm.search import SearchResponse

        response = SearchResponse(
            query="obscure query",
            results=[],
            summary="No results found",
        )

        assert len(response.results) == 0
        assert response.summary == "No results found"


class TestWebSearcher:
    """Tests for WebSearcher class."""

    def test_create_web_searcher(self) -> None:
        """Test creating a WebSearcher instance."""
        from ara.llm.search import WebSearcher

        searcher = WebSearcher()
        assert searcher is not None

    def test_create_with_custom_max_results(self) -> None:
        """Test creating searcher with custom max results."""
        from ara.llm.search import WebSearcher

        searcher = WebSearcher(max_results=5)
        assert searcher.max_results == 5

    @patch("ara.llm.search.DDGS")
    @patch("ara.llm.search.DDGS_AVAILABLE", True)
    def test_search_returns_results(self, mock_ddgs: MagicMock) -> None:
        """Test search returns search results."""
        from ara.llm.search import WebSearcher

        # Mock DuckDuckGo response using context manager
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {
                "title": "Raspberry Pi 5",
                "href": "https://raspberrypi.org/pi5",
                "body": "The latest Raspberry Pi model",
            },
            {
                "title": "Pi 5 Review",
                "href": "https://example.com/review",
                "body": "Our review of the Pi 5",
            },
        ]
        mock_ddgs.return_value.__enter__.return_value = mock_instance
        mock_ddgs.return_value.__exit__.return_value = None

        searcher = WebSearcher(max_results=3)
        results = searcher.search("Raspberry Pi 5")

        assert len(results) == 2
        assert results[0].title == "Raspberry Pi 5"
        assert results[0].url == "https://raspberrypi.org/pi5"

    @patch("ara.llm.search.DDGS")
    def test_search_handles_empty_results(self, mock_ddgs: MagicMock) -> None:
        """Test search handles empty results gracefully."""
        from ara.llm.search import WebSearcher

        mock_instance = MagicMock()
        mock_instance.text.return_value = []
        mock_ddgs.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_ddgs.return_value.__exit__ = MagicMock()

        searcher = WebSearcher()
        results = searcher.search("xyznonexistent12345")

        assert len(results) == 0

    @patch("ara.llm.search.DDGS")
    def test_search_handles_error(self, mock_ddgs: MagicMock) -> None:
        """Test search handles errors gracefully."""
        from ara.llm.search import WebSearcher

        mock_instance = MagicMock()
        mock_instance.text.side_effect = Exception("Network error")
        mock_ddgs.return_value.__enter__ = MagicMock(return_value=mock_instance)
        mock_ddgs.return_value.__exit__ = MagicMock()

        searcher = WebSearcher()
        results = searcher.search("test query")

        assert len(results) == 0

    def test_format_results_for_llm(self) -> None:
        """Test formatting search results for LLM context."""
        from ara.llm.search import SearchResult, WebSearcher

        results = [
            SearchResult("Title 1", "https://example1.com", "First snippet"),
            SearchResult("Title 2", "https://example2.com", "Second snippet"),
        ]

        searcher = WebSearcher()
        formatted = searcher.format_results_for_llm(results)

        assert "Title 1" in formatted
        assert "First snippet" in formatted
        assert "Title 2" in formatted
        assert "Second snippet" in formatted


class TestSearchSummarizer:
    """Tests for SearchSummarizer class."""

    def test_create_summarizer(self) -> None:
        """Test creating a SearchSummarizer."""
        from ara.llm.mock import MockLanguageModel
        from ara.llm.search import SearchSummarizer

        llm = MockLanguageModel()
        summarizer = SearchSummarizer(llm=llm)

        assert summarizer is not None

    def test_summarize_results(self) -> None:
        """Test summarizing search results."""
        from ara.llm.mock import MockLanguageModel
        from ara.llm.search import SearchResult, SearchSummarizer

        llm = MockLanguageModel()
        llm.set_response("The Raspberry Pi 5 is a powerful single-board computer.")

        summarizer = SearchSummarizer(llm=llm)
        results = [
            SearchResult("Pi 5", "https://example.com", "Pi 5 specs"),
        ]

        summary = summarizer.summarize("What is Raspberry Pi 5?", results)

        assert "Raspberry Pi 5" in summary
        assert "single-board computer" in summary

    def test_summarize_empty_results(self) -> None:
        """Test summarizing when no results."""
        from ara.llm.mock import MockLanguageModel
        from ara.llm.search import SearchSummarizer

        llm = MockLanguageModel()
        summarizer = SearchSummarizer(llm=llm)

        summary = summarizer.summarize("obscure query", [])

        assert "no results" in summary.lower() or "couldn't find" in summary.lower()


class TestSearchIntentDetection:
    """Tests for detecting search intent in queries."""

    def test_detect_search_intent(self) -> None:
        """Test detecting explicit search requests."""
        from ara.router.intent import IntentClassifier, IntentType

        classifier = IntentClassifier()

        # Explicit search requests
        intent = classifier.classify("search for Raspberry Pi 5")
        assert intent.type == IntentType.WEB_SEARCH
        assert "Raspberry Pi 5" in intent.entities.get("query", "")

    def test_detect_with_internet_trigger(self) -> None:
        """Test detecting 'with internet' trigger."""
        from ara.router.intent import IntentClassifier, IntentType

        classifier = IntentClassifier()

        intent = classifier.classify("with internet, what is the weather today")
        assert intent.type == IntentType.WEB_SEARCH

    def test_detect_look_up(self) -> None:
        """Test detecting 'look up' trigger."""
        from ara.router.intent import IntentClassifier, IntentType

        classifier = IntentClassifier()

        intent = classifier.classify("look up the latest news about AI")
        assert intent.type == IntentType.WEB_SEARCH

    def test_regular_question_not_search(self) -> None:
        """Test regular questions are not classified as search."""
        from ara.router.intent import IntentClassifier, IntentType

        classifier = IntentClassifier()

        intent = classifier.classify("what time is it")
        assert intent.type != IntentType.WEB_SEARCH
