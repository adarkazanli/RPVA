"""Unit tests for event extraction and pairing.

Tests EventExtractor pattern matching and EventPairer semantic similarity.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from ara.storage.events import ActivityRepository, EventRepository
from ara.storage.extraction import EventExtractor, EventPairer
from ara.storage.models import ActivityStatus, EventDTO, EventType


class TestEventExtractor:
    """Tests for EventExtractor pattern matching."""

    @pytest.fixture
    def extractor(self) -> EventExtractor:
        """Create an EventExtractor instance."""
        return EventExtractor()

    def test_extract_activity_start_going_to(self, extractor: EventExtractor) -> None:
        """Test extraction of 'going to the gym' pattern."""
        events = extractor.extract("I'm going to the gym", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_START
        assert events[0].context == "gym"
        assert events[0].extraction_confidence == 1.0

    def test_extract_activity_start_heading_to(self, extractor: EventExtractor) -> None:
        """Test extraction of 'heading to' pattern."""
        events = extractor.extract("I'm heading to shower", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_START
        assert events[0].context == "shower"

    def test_extract_activity_start_starting(self, extractor: EventExtractor) -> None:
        """Test extraction of 'starting my workout' pattern."""
        events = extractor.extract("I'm starting my workout", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_START
        assert events[0].context == "workout"
        assert events[0].extraction_confidence == 0.95

    def test_extract_activity_start_about_to(self, extractor: EventExtractor) -> None:
        """Test extraction of 'about to start' pattern."""
        events = extractor.extract("I'm about to start cooking", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_START
        assert events[0].context == "cooking"

    def test_extract_activity_start_taking(self, extractor: EventExtractor) -> None:
        """Test extraction of 'going to take a shower' pattern."""
        events = extractor.extract("I'm going to take a shower", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_START
        assert events[0].context == "shower"

    def test_extract_activity_end_done(self, extractor: EventExtractor) -> None:
        """Test extraction of 'I'm done with' pattern."""
        events = extractor.extract("I'm done with my workout", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_END
        assert events[0].context == "workout"

    def test_extract_activity_end_finished(self, extractor: EventExtractor) -> None:
        """Test extraction of 'just finished' pattern."""
        events = extractor.extract("Just finished my shower", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_END
        assert events[0].context == "shower"

    def test_extract_activity_end_back(self, extractor: EventExtractor) -> None:
        """Test extraction of 'I'm back' pattern."""
        events = extractor.extract("I'm back from the gym", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_END
        assert "gym" in events[0].context.lower() or events[0].context == "activity"

    def test_extract_activity_end_leaving(self, extractor: EventExtractor) -> None:
        """Test extraction of 'leaving the' pattern."""
        events = extractor.extract("I'm leaving the office", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_END
        assert events[0].context == "office"

    def test_extract_note_remember(self, extractor: EventExtractor) -> None:
        """Test extraction of 'remember' pattern."""
        events = extractor.extract("Remember to call mom tomorrow", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.NOTE
        assert "call mom" in events[0].context

    def test_extract_note_parking(self, extractor: EventExtractor) -> None:
        """Test extraction of parking location pattern."""
        events = extractor.extract("I parked at level 3", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.NOTE
        assert "level 3" in events[0].context

    def test_extract_note_make_a_note(self, extractor: EventExtractor) -> None:
        """Test extraction of 'make a note' pattern."""
        events = extractor.extract("Make a note: buy groceries", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.NOTE
        assert "buy groceries" in events[0].context

    def test_extract_no_match(self, extractor: EventExtractor) -> None:
        """Test that random text returns empty list."""
        events = extractor.extract("What's the weather like?", "int-123")

        assert len(events) == 0

    def test_extract_sets_interaction_id(self, extractor: EventExtractor) -> None:
        """Test that interaction_id is properly set."""
        events = extractor.extract("I'm going to the gym", "test-int-456")

        assert len(events) == 1
        assert events[0].interaction_id == "test-int-456"

    def test_extract_sets_source_text(self, extractor: EventExtractor) -> None:
        """Test that source_text captures original transcript."""
        transcript = "I'm going to the gym"
        events = extractor.extract(transcript, "int-123")

        assert len(events) == 1
        assert events[0].source_text == transcript

    def test_extract_case_insensitive(self, extractor: EventExtractor) -> None:
        """Test that extraction is case insensitive."""
        events = extractor.extract("I'M GOING TO THE GYM", "int-123")

        assert len(events) == 1
        assert events[0].event_type == EventType.ACTIVITY_START

    def test_extract_multiple_events(self, extractor: EventExtractor) -> None:
        """Test extraction with start and note in same text."""
        events = extractor.extract("I'm going to the gym, remember towel", "int-123")

        # Should extract both start and note
        assert len(events) >= 1
        event_types = {e.event_type for e in events}
        assert EventType.ACTIVITY_START in event_types


class TestEventPairer:
    """Tests for EventPairer semantic similarity and matching."""

    @pytest.fixture
    def mock_event_repo(self) -> MagicMock:
        """Create mock EventRepository."""
        return MagicMock(spec=EventRepository)

    @pytest.fixture
    def mock_activity_repo(self) -> MagicMock:
        """Create mock ActivityRepository."""
        return MagicMock(spec=ActivityRepository)

    @pytest.fixture
    def pairer(
        self, mock_event_repo: MagicMock, mock_activity_repo: MagicMock
    ) -> EventPairer:
        """Create an EventPairer instance."""
        return EventPairer(mock_event_repo, mock_activity_repo)

    def test_similarity_exact_match(self, pairer: EventPairer) -> None:
        """Test that exact match returns 1.0."""
        score = pairer.calculate_similarity("gym", "gym")
        assert score == 1.0

    def test_similarity_case_insensitive(self, pairer: EventPairer) -> None:
        """Test that similarity is case insensitive."""
        score = pairer.calculate_similarity("GYM", "gym")
        assert score == 1.0

    def test_similarity_substring(self, pairer: EventPairer) -> None:
        """Test that substring match returns 0.9."""
        score = pairer.calculate_similarity("gym", "going to gym")
        assert score == 0.9

    def test_similarity_synonyms(self, pairer: EventPairer) -> None:
        """Test that synonyms return 0.8."""
        score = pairer.calculate_similarity("gym", "workout")
        assert score == 0.8

    def test_similarity_reverse_synonyms(self, pairer: EventPairer) -> None:
        """Test that reverse synonym lookup works."""
        score = pairer.calculate_similarity("workout", "gym")
        assert score == 0.8

    def test_similarity_no_match(self, pairer: EventPairer) -> None:
        """Test that unrelated words return 0."""
        score = pairer.calculate_similarity("gym", "cooking")
        assert score == 0.0

    def test_similarity_word_overlap(self, pairer: EventPairer) -> None:
        """Test that partial word overlap returns partial score."""
        score = pairer.calculate_similarity("morning walk", "evening walk")
        assert 0 < score < 0.9  # Some overlap but not perfect

    def test_find_matching_start_returns_best_match(
        self, pairer: EventPairer, mock_event_repo: MagicMock
    ) -> None:
        """Test that find_matching_start returns highest scoring candidate."""
        now = datetime.now(UTC)
        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=now,
            event_type=EventType.ACTIVITY_END,
            context="workout",
            source_text="done with workout",
            extraction_confidence=0.95,
        )

        # Create candidates with different similarity scores
        candidates = [
            EventDTO(
                id="start-1",
                interaction_id="int-1",
                timestamp=now - timedelta(minutes=30),
                event_type=EventType.ACTIVITY_START,
                context="gym",  # Synonym of workout
                source_text="going to gym",
                extraction_confidence=0.95,
            ),
            EventDTO(
                id="start-2",
                interaction_id="int-2",
                timestamp=now - timedelta(minutes=45),
                event_type=EventType.ACTIVITY_START,
                context="workout",  # Exact match
                source_text="starting workout",
                extraction_confidence=0.95,
            ),
        ]

        mock_event_repo.find_unlinked_start_events.return_value = candidates

        result = pairer.find_matching_start(end_event)

        assert result is not None
        assert result.context == "workout"  # Exact match should win

    def test_find_matching_start_respects_temporal_order(
        self, pairer: EventPairer, mock_event_repo: MagicMock
    ) -> None:
        """Test that events after end_event are excluded."""
        now = datetime.now(UTC)
        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=now,
            event_type=EventType.ACTIVITY_END,
            context="gym",
            source_text="done at gym",
            extraction_confidence=0.95,
        )

        # Candidate is AFTER end event (wrong order)
        candidates = [
            EventDTO(
                id="start-1",
                interaction_id="int-1",
                timestamp=now + timedelta(minutes=30),  # After end
                event_type=EventType.ACTIVITY_START,
                context="gym",
                source_text="going to gym",
                extraction_confidence=0.95,
            ),
        ]

        mock_event_repo.find_unlinked_start_events.return_value = candidates

        result = pairer.find_matching_start(end_event)

        assert result is None

    def test_find_matching_start_no_candidates(
        self, pairer: EventPairer, mock_event_repo: MagicMock
    ) -> None:
        """Test that empty candidates returns None."""
        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=datetime.now(UTC),
            event_type=EventType.ACTIVITY_END,
            context="gym",
            source_text="done at gym",
            extraction_confidence=0.95,
        )

        mock_event_repo.find_unlinked_start_events.return_value = []

        result = pairer.find_matching_start(end_event)

        assert result is None

    def test_find_matching_start_below_min_score(
        self, pairer: EventPairer, mock_event_repo: MagicMock
    ) -> None:
        """Test that low-scoring matches are rejected."""
        now = datetime.now(UTC)
        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=now,
            event_type=EventType.ACTIVITY_END,
            context="cooking",
            source_text="done cooking",
            extraction_confidence=0.95,
        )

        # Candidate has no similarity to "cooking"
        candidates = [
            EventDTO(
                id="start-1",
                interaction_id="int-1",
                timestamp=now - timedelta(minutes=30),
                event_type=EventType.ACTIVITY_START,
                context="swimming",  # No match
                source_text="going swimming",
                extraction_confidence=0.95,
            ),
        ]

        mock_event_repo.find_unlinked_start_events.return_value = candidates

        result = pairer.find_matching_start(end_event, min_score=0.7)

        assert result is None

    def test_pair_event_creates_activity(
        self, pairer: EventPairer, mock_event_repo: MagicMock, mock_activity_repo: MagicMock
    ) -> None:
        """Test that pair_event creates and saves activity."""
        now = datetime.now(UTC)
        start_time = now - timedelta(minutes=30)

        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=now,
            event_type=EventType.ACTIVITY_END,
            context="gym",
            source_text="done at gym",
            extraction_confidence=0.95,
        )

        start_event = EventDTO(
            id="start-1",
            interaction_id="int-1",
            timestamp=start_time,
            event_type=EventType.ACTIVITY_START,
            context="gym",
            source_text="going to gym",
            extraction_confidence=0.95,
        )

        mock_event_repo.find_unlinked_start_events.return_value = [start_event]

        result = pairer.pair_event(end_event)

        assert result is not None
        assert result.name == "gym"
        assert result.status == ActivityStatus.COMPLETED
        assert result.start_event_id == "start-1"
        assert result.end_event_id == "end-1"
        assert result.duration_ms == 30 * 60 * 1000  # 30 minutes
        mock_activity_repo.save.assert_called_once()

    def test_pair_event_links_events(
        self, pairer: EventPairer, mock_event_repo: MagicMock, mock_activity_repo: MagicMock  # noqa: ARG002
    ) -> None:
        """Test that pair_event links start and end events."""
        now = datetime.now(UTC)

        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=now,
            event_type=EventType.ACTIVITY_END,
            context="gym",
            source_text="done at gym",
            extraction_confidence=0.95,
        )

        start_event = EventDTO(
            id="start-1",
            interaction_id="int-1",
            timestamp=now - timedelta(minutes=30),
            event_type=EventType.ACTIVITY_START,
            context="gym",
            source_text="going to gym",
            extraction_confidence=0.95,
        )

        mock_event_repo.find_unlinked_start_events.return_value = [start_event]

        pairer.pair_event(end_event)

        mock_event_repo.link_events.assert_called_once_with("start-1", "end-1")

    def test_pair_event_no_match(
        self, pairer: EventPairer, mock_event_repo: MagicMock, mock_activity_repo: MagicMock
    ) -> None:
        """Test that pair_event returns None when no match found."""
        end_event = EventDTO(
            id="end-1",
            interaction_id="int-1",
            timestamp=datetime.now(UTC),
            event_type=EventType.ACTIVITY_END,
            context="gym",
            source_text="done at gym",
            extraction_confidence=0.95,
        )

        mock_event_repo.find_unlinked_start_events.return_value = []

        result = pairer.pair_event(end_event)

        assert result is None
        mock_activity_repo.save.assert_not_called()


class TestEventPairerSynonyms:
    """Tests for EventPairer synonym handling."""

    def test_default_synonyms_gym(self) -> None:
        """Test default synonyms for gym."""
        mock_event_repo = MagicMock(spec=EventRepository)
        mock_activity_repo = MagicMock(spec=ActivityRepository)
        pairer = EventPairer(mock_event_repo, mock_activity_repo)

        # Test gym synonyms
        assert pairer.calculate_similarity("gym", "workout") == 0.8
        assert pairer.calculate_similarity("gym", "training") == 0.8
        assert pairer.calculate_similarity("gym", "exercise") == 0.8

    def test_default_synonyms_shower(self) -> None:
        """Test default synonyms for shower."""
        mock_event_repo = MagicMock(spec=EventRepository)
        mock_activity_repo = MagicMock(spec=ActivityRepository)
        pairer = EventPairer(mock_event_repo, mock_activity_repo)

        # Test shower synonyms
        assert pairer.calculate_similarity("shower", "bath") == 0.8

    def test_default_synonyms_meal(self) -> None:
        """Test default synonyms for meals."""
        mock_event_repo = MagicMock(spec=EventRepository)
        mock_activity_repo = MagicMock(spec=ActivityRepository)
        pairer = EventPairer(mock_event_repo, mock_activity_repo)

        # Test meal synonyms
        assert pairer.calculate_similarity("lunch", "eating") == 0.8
        assert pairer.calculate_similarity("dinner", "meal") == 0.8
