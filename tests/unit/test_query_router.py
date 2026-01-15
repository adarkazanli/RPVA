"""Unit tests for QueryRouter.

Tests query classification and routing decisions.
"""

import pytest

from ara.router.query_router import (
    DataSource,
    QueryRouter,
    QueryType,
    RoutingDecision,
)


@pytest.fixture
def router() -> QueryRouter:
    """Create a QueryRouter instance for testing."""
    return QueryRouter()


class TestQueryType:
    """Tests for QueryType enum."""

    def test_query_type_values(self) -> None:
        """Test that all expected query types exist."""
        assert QueryType.PERSONAL_DATA.value == "personal_data"
        assert QueryType.FACTUAL_CURRENT.value == "factual_current"
        assert QueryType.GENERAL_KNOWLEDGE.value == "general_knowledge"
        assert QueryType.AMBIGUOUS.value == "ambiguous"


class TestDataSource:
    """Tests for DataSource enum."""

    def test_data_source_values(self) -> None:
        """Test that all expected data sources exist."""
        assert DataSource.DATABASE.value == "database"
        assert DataSource.WEB_SEARCH.value == "web_search"
        assert DataSource.LLM.value == "llm"


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_routing_decision_defaults(self) -> None:
        """Test RoutingDecision default values."""
        decision = RoutingDecision(
            query_type=QueryType.PERSONAL_DATA,
            primary_source=DataSource.DATABASE,
        )
        assert decision.fallback_source is None
        assert decision.confidence == 0.5
        assert decision.indicators_matched == []
        assert decision.should_caveat is False

    def test_routing_decision_full(self) -> None:
        """Test RoutingDecision with all fields."""
        decision = RoutingDecision(
            query_type=QueryType.FACTUAL_CURRENT,
            primary_source=DataSource.WEB_SEARCH,
            fallback_source=DataSource.LLM,
            confidence=0.85,
            indicators_matched=["weather", "temperature"],
            should_caveat=True,
        )
        assert decision.query_type == QueryType.FACTUAL_CURRENT
        assert decision.primary_source == DataSource.WEB_SEARCH
        assert decision.fallback_source == DataSource.LLM
        assert decision.confidence == 0.85
        assert decision.indicators_matched == ["weather", "temperature"]
        assert decision.should_caveat is True


class TestPersonalQueryClassification:
    """Tests for US1: Personal queries route to database first."""

    def test_personal_query_last_exercise(self, router: QueryRouter) -> None:
        """Test: personal query 'When did I last exercise?' returns PERSONAL_DATA type."""
        decision = router.classify("When did I last exercise?")
        assert decision.query_type == QueryType.PERSONAL_DATA

    def test_personal_query_routes_to_database(self, router: QueryRouter) -> None:
        """Test: personal query 'What meetings did I have?' routes to DATABASE."""
        decision = router.classify("What meetings did I have?")
        assert decision.primary_source == DataSource.DATABASE

    def test_personal_query_no_fallback(self, router: QueryRouter) -> None:
        """Test: personal query has no fallback (don't hallucinate)."""
        decision = router.classify("When did I last go to the gym?")
        assert decision.fallback_source is None

    def test_personal_query_my_pattern(self, router: QueryRouter) -> None:
        """Test: 'my workout' pattern is classified as personal."""
        decision = router.classify("What was my workout routine?")
        assert decision.query_type == QueryType.PERSONAL_DATA

    def test_personal_query_have_i_pattern(self, router: QueryRouter) -> None:
        """Test: 'have I' pattern is classified as personal."""
        decision = router.classify("Have I been to the dentist recently?")
        assert decision.query_type == QueryType.PERSONAL_DATA

    def test_personal_query_did_i_mention(self, router: QueryRouter) -> None:
        """Test: 'did I mention' pattern is classified as personal."""
        decision = router.classify("Did I mention anything about the project?")
        assert decision.query_type == QueryType.PERSONAL_DATA


class TestFactualQueryClassification:
    """Tests for US2: Factual queries route to web search."""

    def test_factual_query_weather(self, router: QueryRouter) -> None:
        """Test: factual query 'What's the weather?' returns FACTUAL_CURRENT type."""
        decision = router.classify("What's the weather?")
        assert decision.query_type == QueryType.FACTUAL_CURRENT

    def test_factual_query_routes_to_web_search(self, router: QueryRouter) -> None:
        """Test: distance query 'How far is Dallas?' routes to WEB_SEARCH."""
        decision = router.classify("How far is Dallas?")
        assert decision.primary_source == DataSource.WEB_SEARCH

    def test_factual_query_stock_price(self, router: QueryRouter) -> None:
        """Test: price query 'Apple stock price' routes to WEB_SEARCH."""
        decision = router.classify("What's Apple stock price?")
        assert decision.primary_source == DataSource.WEB_SEARCH

    def test_factual_query_has_llm_fallback(self, router: QueryRouter) -> None:
        """Test: factual query has LLM fallback with caveat."""
        decision = router.classify("What's the weather in Austin?")
        assert decision.fallback_source == DataSource.LLM
        assert decision.should_caveat is True

    def test_factual_query_news(self, router: QueryRouter) -> None:
        """Test: news query routes to web search."""
        decision = router.classify("What's in the news today?")
        assert decision.query_type == QueryType.FACTUAL_CURRENT

    def test_factual_query_score(self, router: QueryRouter) -> None:
        """Test: sports score query routes to web search."""
        decision = router.classify("What's the score of the game?")
        assert decision.query_type == QueryType.FACTUAL_CURRENT


class TestGeneralKnowledgeClassification:
    """Tests for US3: General knowledge queries route to LLM."""

    def test_general_knowledge_definition(self, router: QueryRouter) -> None:
        """Test: definition query 'What does serendipity mean?' returns GENERAL_KNOWLEDGE."""
        decision = router.classify("What does serendipity mean?")
        assert decision.query_type == QueryType.GENERAL_KNOWLEDGE

    def test_general_knowledge_routes_to_llm(self, router: QueryRouter) -> None:
        """Test: how-to query 'How do I make eggs?' routes to LLM."""
        decision = router.classify("How do I make scrambled eggs?")
        assert decision.primary_source == DataSource.LLM

    def test_general_knowledge_no_web_search(self, router: QueryRouter) -> None:
        """Test: general knowledge does NOT trigger web search."""
        decision = router.classify("What is the capital of France?")
        assert decision.primary_source == DataSource.LLM
        # Should NOT route to web search
        assert decision.primary_source != DataSource.WEB_SEARCH

    def test_general_knowledge_explain(self, router: QueryRouter) -> None:
        """Test: explain query routes to LLM."""
        decision = router.classify("Explain photosynthesis")
        assert decision.query_type == QueryType.GENERAL_KNOWLEDGE

    def test_general_knowledge_math(self, router: QueryRouter) -> None:
        """Test: math query routes to LLM."""
        decision = router.classify("Calculate 15 percent of 200")
        assert decision.query_type == QueryType.GENERAL_KNOWLEDGE


class TestAmbiguousQueryClassification:
    """Tests for US4: Ambiguous query classification."""

    def test_ambiguous_query_without_context(self, router: QueryRouter) -> None:
        """Test: ambiguous query without context defaults to GENERAL_KNOWLEDGE."""
        decision = router.classify("What about John?")
        # Without context, defaults to general knowledge
        assert decision.query_type == QueryType.GENERAL_KNOWLEDGE
        assert decision.confidence < 0.7

    def test_ambiguous_query_with_context_resolves(self, router: QueryRouter) -> None:
        """Test: ambiguous query with context resolves to appropriate type."""
        context = {
            "recent_queries": [
                {"query_type": QueryType.PERSONAL_DATA, "query": "When did I meet John?"}
            ]
        }
        decision = router.classify("What about that?", context)
        # With personal context, should resolve to personal
        assert decision.query_type == QueryType.PERSONAL_DATA


class TestHelperMethods:
    """Tests for is_personal_query and is_factual_query helpers."""

    def test_is_personal_query_true(self, router: QueryRouter) -> None:
        """Test is_personal_query returns True for personal queries."""
        assert router.is_personal_query("When did I last exercise?") is True
        assert router.is_personal_query("my workout") is True
        assert router.is_personal_query("What did I eat?") is True

    def test_is_personal_query_false(self, router: QueryRouter) -> None:
        """Test is_personal_query returns False for non-personal queries."""
        assert router.is_personal_query("What's the weather?") is False
        assert router.is_personal_query("How do I cook eggs?") is False

    def test_is_factual_query_true(self, router: QueryRouter) -> None:
        """Test is_factual_query returns True for factual queries."""
        assert router.is_factual_query("What's the weather in Austin?") is True
        assert router.is_factual_query("stock price of Apple") is True
        assert router.is_factual_query("How far is Dallas?") is True

    def test_is_factual_query_false(self, router: QueryRouter) -> None:
        """Test is_factual_query returns False for non-factual queries."""
        assert router.is_factual_query("What is photosynthesis?") is False
        assert router.is_factual_query("When did I exercise?") is False
