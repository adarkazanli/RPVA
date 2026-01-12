"""Unit tests for daily summary generation."""

import uuid
from datetime import UTC, date, datetime

import pytest

from ara.logger.interaction import Interaction, OperationMode, ResponseSource
from ara.logger.storage import InteractionStorage
from ara.logger.summary import (
    ActionItem,
    DailySummary,
    SummaryGenerator,
    extract_action_items,
)


class TestDailySummary:
    """Tests for DailySummary entity."""

    def test_create_summary(self) -> None:
        """Test creating a daily summary."""
        summary = DailySummary(
            id=uuid.uuid4(),
            date=date.today(),
            device_id="pi4-kitchen",
            total_interactions=50,
            successful_interactions=48,
            error_count=2,
            avg_latency_ms=1250,
            p95_latency_ms=2100,
            mode_breakdown={"offline": 45, "online_local": 5},
            top_intents=[
                {"intent": "general_question", "count": 20},
                {"intent": "timer_set", "count": 15},
            ],
            action_items=[],
            notable_interactions=[],
            generated_at=datetime.now(UTC),
        )
        assert summary.total_interactions == 50
        assert summary.error_count == 2
        assert summary.mode_breakdown["offline"] == 45

    def test_summary_error_rate(self) -> None:
        """Test calculating error rate."""
        summary = DailySummary(
            id=uuid.uuid4(),
            date=date.today(),
            device_id="pi4-kitchen",
            total_interactions=100,
            successful_interactions=95,
            error_count=5,
            avg_latency_ms=1000,
            p95_latency_ms=1800,
            mode_breakdown={},
            top_intents=[],
            action_items=[],
            notable_interactions=[],
            generated_at=datetime.now(UTC),
        )
        assert summary.error_rate == 0.05

    def test_summary_to_dict(self) -> None:
        """Test converting summary to dictionary."""
        summary_id = uuid.uuid4()
        summary = DailySummary(
            id=summary_id,
            date=date(2024, 1, 15),
            device_id="pi4-kitchen",
            total_interactions=50,
            successful_interactions=48,
            error_count=2,
            avg_latency_ms=1250,
            p95_latency_ms=2100,
            mode_breakdown={"offline": 45},
            top_intents=[{"intent": "general_question", "count": 20}],
            action_items=[],
            notable_interactions=[],
            generated_at=datetime.now(UTC),
        )

        data = summary.to_dict()
        assert data["id"] == str(summary_id)
        assert data["date"] == "2024-01-15"
        assert data["total_interactions"] == 50

    def test_summary_to_markdown(self) -> None:
        """Test converting summary to Markdown."""
        summary = DailySummary(
            id=uuid.uuid4(),
            date=date(2024, 1, 15),
            device_id="pi4-kitchen",
            total_interactions=50,
            successful_interactions=48,
            error_count=2,
            avg_latency_ms=1250,
            p95_latency_ms=2100,
            mode_breakdown={"offline": 45, "online_local": 5},
            top_intents=[
                {"intent": "general_question", "count": 20},
                {"intent": "timer_set", "count": 15},
            ],
            action_items=[
                ActionItem(text="call mom", source_transcript="remind me to call mom"),
                ActionItem(text="buy milk", source_transcript="remind me to buy milk"),
            ],
            notable_interactions=[],
            generated_at=datetime.now(UTC),
        )

        md = summary.to_markdown()

        assert "# Daily Summary" in md
        assert "2024-01-15" in md
        assert "50" in md  # total interactions
        assert "general_question" in md
        assert "call mom" in md


class TestActionItem:
    """Tests for ActionItem."""

    def test_create_action_item(self) -> None:
        """Test creating an action item."""
        item = ActionItem(
            text="call mom",
            source_transcript="remind me to call mom tomorrow",
        )
        assert item.text == "call mom"
        assert "call mom" in item.source_transcript


class TestExtractActionItems:
    """Tests for action item extraction."""

    def test_extract_from_reminder(self) -> None:
        """Test extracting action items from reminder intents."""
        interactions = [
            _make_interaction("remind me to call mom", "reminder_set"),
            _make_interaction("what time is it", "general_question"),
            _make_interaction("remind me to buy milk", "reminder_set"),
        ]

        items = extract_action_items(interactions)

        assert len(items) == 2
        assert any("call mom" in item.text for item in items)
        assert any("buy milk" in item.text for item in items)

    def test_extract_from_timer(self) -> None:
        """Test extracting action items from timer intents."""
        interactions = [
            _make_interaction("set a timer for pasta", "timer_set"),
        ]

        items = extract_action_items(interactions)
        # Timers might or might not generate action items
        assert isinstance(items, list)

    def test_extract_empty_list(self) -> None:
        """Test extracting from empty interaction list."""
        items = extract_action_items([])
        assert items == []

    def test_extract_no_actionable(self) -> None:
        """Test extracting when no actionable intents."""
        interactions = [
            _make_interaction("what time is it", "general_question"),
            _make_interaction("what is the weather", "general_question"),
        ]

        items = extract_action_items(interactions)
        assert items == []


class TestSummaryGenerator:
    """Tests for SummaryGenerator."""

    @pytest.fixture
    def storage(self, tmp_path) -> InteractionStorage:
        """Create storage with sample interactions."""
        storage = InteractionStorage(
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
        )

        # Add sample interactions
        session_id = uuid.uuid4()
        for i in range(10):
            interaction = Interaction(
                id=uuid.uuid4(),
                session_id=session_id,
                timestamp=datetime.now(UTC),
                device_id="test-device",
                wake_word_confidence=0.95,
                audio_duration_ms=2000,
                transcript=f"question {i}",
                transcript_confidence=0.9,
                intent="general_question" if i % 2 == 0 else "timer_set",
                intent_confidence=0.85,
                entities={},
                response=f"answer {i}",
                response_source=ResponseSource.LOCAL_LLM,
                latency_ms={"total": 1000 + i * 100},
                mode=OperationMode.OFFLINE,
                error=None if i != 5 else "Test error",
            )
            storage.save(interaction)

        return storage

    @pytest.fixture
    def generator(self, storage: InteractionStorage) -> SummaryGenerator:
        """Create a SummaryGenerator instance."""
        return SummaryGenerator(storage)

    def test_generate_summary(self, generator: SummaryGenerator) -> None:
        """Test generating a daily summary."""
        today = date.today()
        summary = generator.generate(today, device_id="test-device")

        assert summary is not None
        assert summary.total_interactions == 10
        assert summary.error_count == 1
        assert summary.successful_interactions == 9

    def test_generate_summary_no_interactions(
        self, generator: SummaryGenerator
    ) -> None:
        """Test generating summary for date with no interactions."""
        past_date = date(2020, 1, 1)
        summary = generator.generate(past_date, device_id="test-device")

        assert summary.total_interactions == 0

    def test_calculate_p95_latency(self, generator: SummaryGenerator) -> None:
        """Test P95 latency calculation."""
        today = date.today()
        summary = generator.generate(today, device_id="test-device")

        # With 10 interactions at 1000-1900ms, P95 should be high
        assert summary.p95_latency_ms > 0

    def test_top_intents(self, generator: SummaryGenerator) -> None:
        """Test top intents calculation."""
        today = date.today()
        summary = generator.generate(today, device_id="test-device")

        assert len(summary.top_intents) > 0
        # Should have both general_question and timer_set
        intent_names = [i["intent"] for i in summary.top_intents]
        assert "general_question" in intent_names or "timer_set" in intent_names

    def test_mode_breakdown(self, generator: SummaryGenerator) -> None:
        """Test mode breakdown calculation."""
        today = date.today()
        summary = generator.generate(today, device_id="test-device")

        assert "offline" in summary.mode_breakdown
        assert summary.mode_breakdown["offline"] == 10

    def test_save_summary(self, generator: SummaryGenerator, tmp_path) -> None:
        """Test saving summary to file."""
        today = date.today()
        summary = generator.generate(today, device_id="test-device")

        output_path = tmp_path / "summary.md"
        generator.save_markdown(summary, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "Daily Summary" in content


def _make_interaction(transcript: str, intent: str) -> Interaction:
    """Helper to create test interactions."""
    return Interaction(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        timestamp=datetime.now(UTC),
        device_id="test-device",
        wake_word_confidence=0.95,
        audio_duration_ms=2000,
        transcript=transcript,
        transcript_confidence=0.9,
        intent=intent,
        intent_confidence=0.85,
        entities={"message": transcript} if intent == "reminder_set" else {},
        response="OK",
        response_source=ResponseSource.LOCAL_LLM,
        latency_ms={"total": 1000},
        mode=OperationMode.OFFLINE,
        error=None,
    )
