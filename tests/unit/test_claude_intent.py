"""Unit tests for Claude intent classification.

Tests the CLAUDE_QUERY, CLAUDE_SUMMARY, and CLAUDE_RESET intent patterns.
"""

import pytest

from ara.router.intent import IntentClassifier, IntentType


class TestClaudeQueryIntent:
    """Tests for CLAUDE_QUERY intent recognition."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create intent classifier instance."""
        return IntentClassifier()

    def test_ask_claude_basic_question(self, classifier: IntentClassifier) -> None:
        """Test 'ask Claude what is X' pattern."""
        result = classifier.classify("ask Claude what is the capital of France")
        assert result.type == IntentType.CLAUDE_QUERY
        assert result.confidence >= 0.9
        assert "query" in result.entities
        assert "capital of France" in result.entities["query"]

    def test_ask_claude_with_variations(self, classifier: IntentClassifier) -> None:
        """Test various 'ask Claude' trigger variations."""
        test_cases = [
            "ask claude to explain quantum computing",
            "hey claude, what is machine learning",
            "claude, tell me about Python",
        ]
        for text in test_cases:
            result = classifier.classify(text)
            assert result.type == IntentType.CLAUDE_QUERY, f"Failed for: {text}"
            assert "query" in result.entities, f"No query entity for: {text}"

    def test_ask_claud_mishearing(self, classifier: IntentClassifier) -> None:
        """Test 'ask Claud' (common mishearing) pattern."""
        result = classifier.classify("ask claud what time is it in Tokyo")
        assert result.type == IntentType.CLAUDE_QUERY
        assert "query" in result.entities

    def test_ask_claude_extracts_full_query(self, classifier: IntentClassifier) -> None:
        """Test that full query text is captured."""
        result = classifier.classify(
            "ask Claude how do I make a chocolate cake from scratch"
        )
        assert result.type == IntentType.CLAUDE_QUERY
        assert "chocolate cake" in result.entities["query"]

    def test_non_claude_query_not_matched(self, classifier: IntentClassifier) -> None:
        """Test that regular questions don't match Claude intent."""
        result = classifier.classify("what is the weather today")
        assert result.type != IntentType.CLAUDE_QUERY


class TestClaudeSummaryIntent:
    """Tests for CLAUDE_SUMMARY intent recognition."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create intent classifier instance."""
        return IntentClassifier()

    def test_summarize_claude_conversations_today(
        self, classifier: IntentClassifier
    ) -> None:
        """Test summarize conversations today pattern."""
        result = classifier.classify("summarize my Claude conversations today")
        assert result.type == IntentType.CLAUDE_SUMMARY
        assert result.confidence >= 0.9
        assert result.entities.get("period") == "today"

    def test_summarize_claude_conversations_this_week(
        self, classifier: IntentClassifier
    ) -> None:
        """Test summarize conversations this week pattern."""
        result = classifier.classify("summarize my Claude conversations this week")
        assert result.type == IntentType.CLAUDE_SUMMARY
        assert result.entities.get("period") == "week"

    def test_summarize_claude_conversations_this_month(
        self, classifier: IntentClassifier
    ) -> None:
        """Test summarize conversations this month pattern."""
        result = classifier.classify("what did I ask Claude this month")
        assert result.type == IntentType.CLAUDE_SUMMARY
        assert result.entities.get("period") == "month"

    def test_key_learnings_from_claude(self, classifier: IntentClassifier) -> None:
        """Test 'key learnings from Claude' pattern."""
        result = classifier.classify("what are my key learnings from Claude today")
        assert result.type == IntentType.CLAUDE_SUMMARY
        assert "today" in result.entities.get("period", "") or result.entities.get("period") == "today"

    def test_what_did_i_ask_claude(self, classifier: IntentClassifier) -> None:
        """Test 'what did I ask Claude' pattern."""
        result = classifier.classify("what did I ask Claude yesterday")
        assert result.type == IntentType.CLAUDE_SUMMARY
        assert result.entities.get("period") == "yesterday"

    def test_claude_conversation_history(self, classifier: IntentClassifier) -> None:
        """Test Claude conversation history pattern."""
        result = classifier.classify("show me my Claude conversation history")
        assert result.type == IntentType.CLAUDE_SUMMARY

    def test_recap_claude_discussions(self, classifier: IntentClassifier) -> None:
        """Test recap Claude discussions pattern."""
        result = classifier.classify("give me a recap of my Claude discussions")
        assert result.type == IntentType.CLAUDE_SUMMARY


class TestClaudeResetIntent:
    """Tests for CLAUDE_RESET intent recognition."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create intent classifier instance."""
        return IntentClassifier()

    def test_new_conversation_pattern(self, classifier: IntentClassifier) -> None:
        """Test 'new conversation' pattern."""
        result = classifier.classify("new conversation")
        assert result.type == IntentType.CLAUDE_RESET
        assert result.confidence >= 0.9

    def test_start_over_pattern(self, classifier: IntentClassifier) -> None:
        """Test 'start over' pattern."""
        result = classifier.classify("start over")
        assert result.type == IntentType.CLAUDE_RESET

    def test_start_fresh_pattern(self, classifier: IntentClassifier) -> None:
        """Test 'start fresh' pattern."""
        result = classifier.classify("start fresh")
        assert result.type == IntentType.CLAUDE_RESET

    def test_reset_conversation_pattern(self, classifier: IntentClassifier) -> None:
        """Test 'reset conversation' pattern."""
        result = classifier.classify("reset the conversation")
        assert result.type == IntentType.CLAUDE_RESET

    def test_clear_conversation_pattern(self, classifier: IntentClassifier) -> None:
        """Test 'clear conversation' pattern."""
        result = classifier.classify("clear conversation history")
        assert result.type == IntentType.CLAUDE_RESET

    def test_forget_conversation_pattern(self, classifier: IntentClassifier) -> None:
        """Test 'forget our conversation' pattern."""
        result = classifier.classify("forget our conversation")
        assert result.type == IntentType.CLAUDE_RESET
