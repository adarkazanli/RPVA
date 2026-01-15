"""Integration tests for Smart Query Routing flow.

Tests the complete routing flow through the Orchestrator:
- Personal queries → MongoDB → "not found" if empty
- Factual queries → Web search → LLM fallback with caveat
- General knowledge → LLM directly
"""

from unittest.mock import MagicMock, patch

import pytest

from ara.router.orchestrator import Orchestrator
from ara.router.query_router import QueryRouter


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock LLM."""
    llm = MagicMock()
    llm.generate.return_value = MagicMock(text="This is an LLM response.")
    return llm


@pytest.fixture
def mock_feedback() -> MagicMock:
    """Create a mock feedback."""
    return MagicMock()


@pytest.fixture
def orchestrator(mock_llm: MagicMock, mock_feedback: MagicMock) -> Orchestrator:
    """Create an Orchestrator with mocked components."""
    return Orchestrator(llm=mock_llm, feedback=mock_feedback)


class TestPersonalQueryRouting:
    """Tests for US1: Personal queries check database first."""

    def test_personal_query_no_storage_returns_not_found(self, orchestrator: Orchestrator) -> None:
        """Test: personal query with no storage returns 'not found' message."""
        response = orchestrator.process("When did I last exercise?")
        assert "don't have any" in response.lower() or "no records" in response.lower()

    def test_personal_query_exercise_returns_exercise_message(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test: exercise query returns exercise-specific not found message."""
        response = orchestrator.process("When did I last exercise?")
        assert "exercise" in response.lower() or "records" in response.lower()

    def test_personal_query_meeting_returns_meeting_message(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test: meeting query returns meeting-specific not found message."""
        response = orchestrator.process("What meetings did I have?")
        assert "meeting" in response.lower() or "records" in response.lower()

    def test_personal_query_does_not_call_llm(
        self, orchestrator: Orchestrator, mock_llm: MagicMock
    ) -> None:
        """Test: personal query does NOT call LLM (prevents hallucination)."""
        orchestrator.process("When did I last go to the gym?")
        # LLM should NOT be called for personal queries
        mock_llm.generate.assert_not_called()


class TestFactualQueryRouting:
    """Tests for US2: Factual queries use web search."""

    def test_factual_query_uses_search_client(
        self, orchestrator: Orchestrator, mock_llm: MagicMock  # noqa: ARG002
    ) -> None:
        """Test: factual query uses search client."""
        with patch.object(orchestrator, "_search_client") as mock_search:
            mock_search.search.return_value = MagicMock(
                success=True,
                answer="It's 72°F and sunny.",
                results=[],
            )
            response = orchestrator.process("What's the weather in Austin?")
            mock_search.search.assert_called_once()
            assert "72" in response or "sunny" in response.lower()

    def test_factual_query_with_search_failure_falls_back_to_llm(
        self, orchestrator: Orchestrator, mock_llm: MagicMock
    ) -> None:
        """Test: factual query falls back to LLM when search fails."""
        with patch.object(orchestrator, "_search_client") as mock_search:
            mock_search.search.side_effect = Exception("Search failed")
            response = orchestrator.process("What's the weather in Austin?")
            # Should fall back to LLM with caveat
            mock_llm.generate.assert_called_once()
            assert "couldn't verify" in response.lower() or "llm" in response.lower()

    def test_factual_query_adds_caveat_on_fallback(
        self, orchestrator: Orchestrator, mock_llm: MagicMock  # noqa: ARG002
    ) -> None:
        """Test: factual query adds caveat when falling back to LLM."""
        with patch.object(orchestrator, "_search_client") as mock_search:
            mock_search.search.return_value = MagicMock(
                success=False,
                answer=None,
                results=[],
            )
            response = orchestrator.process("What's the weather in Austin?")
            # Should include caveat prefix
            assert "couldn't verify" in response.lower() or "llm response" in response.lower()


class TestGeneralKnowledgeRouting:
    """Tests for US3: General knowledge uses LLM directly."""

    def test_general_knowledge_uses_llm_directly(
        self, orchestrator: Orchestrator, mock_llm: MagicMock
    ) -> None:
        """Test: general knowledge query uses LLM directly."""
        response = orchestrator.process("What is photosynthesis?")
        mock_llm.generate.assert_called_once()
        assert "LLM response" in response

    def test_general_knowledge_how_to_uses_llm(
        self, orchestrator: Orchestrator, mock_llm: MagicMock
    ) -> None:
        """Test: how-to query uses LLM directly."""
        orchestrator.process("How do I make scrambled eggs?")
        mock_llm.generate.assert_called_once()

    def test_general_knowledge_does_not_call_search(
        self, orchestrator: Orchestrator, mock_llm: MagicMock  # noqa: ARG002
    ) -> None:
        """Test: general knowledge query does NOT call search."""
        with patch.object(orchestrator, "_search_client") as mock_search:
            orchestrator.process("What is the capital of France?")
            mock_search.search.assert_not_called()


class TestRoutingFlow:
    """End-to-end routing flow tests."""

    def test_routing_decision_is_logged(
        self, orchestrator: Orchestrator, mock_llm: MagicMock  # noqa: ARG002
    ) -> None:
        """Test: routing decision is logged for debugging."""
        with patch("ara.router.orchestrator.logger") as mock_logger:
            orchestrator.process("What's the weather?")
            # Should have logged the routing decision
            debug_calls = [
                call
                for call in mock_logger.debug.call_args_list
                if "QueryRouter decision" in str(call)
            ]
            assert len(debug_calls) > 0

    def test_query_router_integration(self, orchestrator: Orchestrator) -> None:
        """Test: QueryRouter is properly integrated."""
        # Verify the router is initialized
        assert orchestrator._query_router is not None
        assert isinstance(orchestrator._query_router, QueryRouter)

    def test_mixed_query_types_route_correctly(
        self, orchestrator: Orchestrator, mock_llm: MagicMock
    ) -> None:
        """Test: different query types route to correct handlers."""
        # Personal query - should NOT call LLM
        orchestrator.process("When did I last exercise?")
        assert mock_llm.generate.call_count == 0

        # General knowledge - should call LLM
        orchestrator.process("What is photosynthesis?")
        assert mock_llm.generate.call_count == 1

        # Reset for next test
        mock_llm.reset_mock()

        # Factual with search success - should NOT call LLM
        with patch.object(orchestrator, "_search_client") as mock_search:
            mock_search.search.return_value = MagicMock(
                success=True,
                answer="72°F",
                results=[],
            )
            orchestrator.process("What's the weather?")
            mock_llm.generate.assert_not_called()
