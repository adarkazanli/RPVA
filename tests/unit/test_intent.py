"""Unit tests for intent classification."""

import pytest

from ara.router.intent import (
    Intent,
    IntentType,
    IntentClassifier,
)


class TestIntentType:
    """Tests for IntentType enum."""

    def test_intent_types_exist(self) -> None:
        """Test all required intent types exist."""
        assert IntentType.GENERAL_QUESTION.value == "general_question"
        assert IntentType.TIMER_SET.value == "timer_set"
        assert IntentType.TIMER_CANCEL.value == "timer_cancel"
        assert IntentType.TIMER_QUERY.value == "timer_query"
        assert IntentType.REMINDER_SET.value == "reminder_set"
        assert IntentType.REMINDER_CANCEL.value == "reminder_cancel"
        assert IntentType.REMINDER_QUERY.value == "reminder_query"
        assert IntentType.SYSTEM_COMMAND.value == "system_command"
        assert IntentType.UNKNOWN.value == "unknown"


class TestIntent:
    """Tests for Intent dataclass."""

    def test_create_intent(self) -> None:
        """Test creating an intent with all fields."""
        intent = Intent(
            type=IntentType.TIMER_SET,
            confidence=0.95,
            entities={"duration": "5 minutes", "name": "pasta"},
            raw_text="set a timer for 5 minutes called pasta",
        )
        assert intent.type == IntentType.TIMER_SET
        assert intent.confidence == 0.95
        assert intent.entities["duration"] == "5 minutes"
        assert intent.entities["name"] == "pasta"

    def test_create_intent_no_entities(self) -> None:
        """Test creating an intent without entities."""
        intent = Intent(
            type=IntentType.GENERAL_QUESTION,
            confidence=0.8,
            entities={},
            raw_text="what time is it",
        )
        assert intent.entities == {}


class TestIntentClassifier:
    """Tests for IntentClassifier."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create an IntentClassifier instance."""
        return IntentClassifier()

    # Timer intents
    def test_classify_timer_set(self, classifier: IntentClassifier) -> None:
        """Test classifying timer set intent."""
        intent = classifier.classify("set a timer for 5 minutes")
        assert intent.type == IntentType.TIMER_SET
        assert intent.confidence >= 0.8
        assert "duration" in intent.entities

    def test_classify_timer_set_with_name(self, classifier: IntentClassifier) -> None:
        """Test classifying timer set with name."""
        intent = classifier.classify("set a 10 minute timer called pasta")
        assert intent.type == IntentType.TIMER_SET
        assert "name" in intent.entities or "duration" in intent.entities

    def test_classify_timer_cancel(self, classifier: IntentClassifier) -> None:
        """Test classifying timer cancel intent."""
        intent = classifier.classify("cancel the timer")
        assert intent.type == IntentType.TIMER_CANCEL
        assert intent.confidence >= 0.8

    def test_classify_timer_cancel_specific(
        self, classifier: IntentClassifier
    ) -> None:
        """Test classifying specific timer cancellation."""
        intent = classifier.classify("cancel the pasta timer")
        assert intent.type == IntentType.TIMER_CANCEL
        assert "name" in intent.entities

    def test_classify_timer_query(self, classifier: IntentClassifier) -> None:
        """Test classifying timer query intent."""
        intent = classifier.classify("how much time is left on my timer")
        assert intent.type == IntentType.TIMER_QUERY
        assert intent.confidence >= 0.8

    def test_classify_timer_query_list(self, classifier: IntentClassifier) -> None:
        """Test classifying timer list query."""
        intent = classifier.classify("what timers do I have")
        assert intent.type == IntentType.TIMER_QUERY

    # Reminder intents
    def test_classify_reminder_set(self, classifier: IntentClassifier) -> None:
        """Test classifying reminder set intent."""
        intent = classifier.classify("remind me to call mom in 1 hour")
        assert intent.type == IntentType.REMINDER_SET
        assert intent.confidence >= 0.8
        assert "message" in intent.entities or "time" in intent.entities

    def test_classify_reminder_set_at_time(
        self, classifier: IntentClassifier
    ) -> None:
        """Test classifying reminder with specific time."""
        intent = classifier.classify("remind me to take medication at 3 PM")
        assert intent.type == IntentType.REMINDER_SET

    def test_classify_reminder_cancel(self, classifier: IntentClassifier) -> None:
        """Test classifying reminder cancel intent."""
        intent = classifier.classify("cancel my reminder")
        assert intent.type == IntentType.REMINDER_CANCEL
        assert intent.confidence >= 0.8

    def test_classify_reminder_query(self, classifier: IntentClassifier) -> None:
        """Test classifying reminder query intent."""
        intent = classifier.classify("what reminders do I have")
        assert intent.type == IntentType.REMINDER_QUERY
        assert intent.confidence >= 0.8

    # General questions
    def test_classify_general_question(self, classifier: IntentClassifier) -> None:
        """Test classifying general question."""
        intent = classifier.classify("what is the capital of France")
        assert intent.type == IntentType.GENERAL_QUESTION

    def test_classify_general_question_time(
        self, classifier: IntentClassifier
    ) -> None:
        """Test classifying time question as general."""
        intent = classifier.classify("what time is it")
        assert intent.type == IntentType.GENERAL_QUESTION

    # System commands
    def test_classify_system_go_offline(self, classifier: IntentClassifier) -> None:
        """Test classifying system offline command."""
        intent = classifier.classify("go offline")
        assert intent.type == IntentType.SYSTEM_COMMAND
        assert intent.entities.get("command") == "offline"

    def test_classify_system_go_online(self, classifier: IntentClassifier) -> None:
        """Test classifying system online command."""
        intent = classifier.classify("go online")
        assert intent.type == IntentType.SYSTEM_COMMAND
        assert intent.entities.get("command") == "online"

    def test_classify_system_status(self, classifier: IntentClassifier) -> None:
        """Test classifying system status query."""
        intent = classifier.classify("what mode are you in")
        assert intent.type == IntentType.SYSTEM_COMMAND
        assert intent.entities.get("command") == "status"

    # Edge cases
    def test_classify_empty_string(self, classifier: IntentClassifier) -> None:
        """Test classifying empty string."""
        intent = classifier.classify("")
        assert intent.type == IntentType.UNKNOWN
        assert intent.confidence < 0.5

    def test_classify_ambiguous(self, classifier: IntentClassifier) -> None:
        """Test classifying ambiguous input."""
        intent = classifier.classify("timer")
        # Should classify but with lower confidence
        assert intent.confidence < 0.9

    def test_classify_preserves_raw_text(self, classifier: IntentClassifier) -> None:
        """Test that raw text is preserved in intent."""
        text = "set a timer for 5 minutes"
        intent = classifier.classify(text)
        assert intent.raw_text == text


class TestIntentEntityExtraction:
    """Tests for entity extraction from intents."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create an IntentClassifier instance."""
        return IntentClassifier()

    def test_extract_timer_duration(self, classifier: IntentClassifier) -> None:
        """Test extracting duration from timer intent."""
        intent = classifier.classify("set a timer for 5 minutes")
        assert "duration" in intent.entities
        assert "5" in intent.entities["duration"] or "minute" in intent.entities["duration"]

    def test_extract_timer_name(self, classifier: IntentClassifier) -> None:
        """Test extracting name from timer intent."""
        intent = classifier.classify("set a timer called pasta for 10 minutes")
        # Should extract either name or duration
        assert len(intent.entities) > 0

    def test_extract_reminder_message(self, classifier: IntentClassifier) -> None:
        """Test extracting message from reminder intent."""
        intent = classifier.classify("remind me to call mom")
        assert "message" in intent.entities or "time" in intent.entities

    def test_extract_reminder_time(self, classifier: IntentClassifier) -> None:
        """Test extracting time from reminder intent."""
        intent = classifier.classify("remind me at 3 PM to take medication")
        # Should extract time or message
        assert len(intent.entities) > 0
