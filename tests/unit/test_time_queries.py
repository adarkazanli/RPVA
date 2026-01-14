"""Unit tests for time-based queries.

Tests duration calculation, formatting, and query logic.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_format_seconds_only(self) -> None:
        """Test formatting durations under 1 minute."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        # 30 seconds
        result = handler.format_duration(30000)
        assert result == "about 30 seconds"

        # 45 seconds
        result = handler.format_duration(45000)
        assert result == "about 45 seconds"

    def test_format_minutes_only(self) -> None:
        """Test formatting durations of minutes."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        # 5 minutes
        result = handler.format_duration(5 * 60 * 1000)
        assert result == "about 5 minutes"

        # 1 minute (singular)
        result = handler.format_duration(60 * 1000)
        assert result == "about 1 minute"

    def test_format_hours_and_minutes(self) -> None:
        """Test formatting durations with hours and minutes."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        # 2 hours and 15 minutes
        result = handler.format_duration((2 * 60 + 15) * 60 * 1000)
        assert result == "about 2 hours and 15 minutes"

        # 1 hour (singular)
        result = handler.format_duration(60 * 60 * 1000)
        assert result == "about 1 hour"

    def test_format_exact_hours(self) -> None:
        """Test formatting exact hour durations."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        # Exactly 3 hours
        result = handler.format_duration(3 * 60 * 60 * 1000)
        assert result == "about 3 hours"

    def test_format_over_24_hours(self) -> None:
        """Test formatting durations over 24 hours."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        # 26 hours
        result = handler.format_duration(26 * 60 * 60 * 1000)
        assert result == "about 1 day and 2 hours"

        # 48 hours
        result = handler.format_duration(48 * 60 * 60 * 1000)
        assert result == "about 2 days"

    def test_format_zero_duration(self) -> None:
        """Test formatting zero duration."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        result = handler.format_duration(0)
        assert result == "less than a second"


class TestDurationCalculation:
    """Tests for duration calculation between events."""

    def test_calculate_duration_from_timestamps(self) -> None:
        """Test calculating duration from two timestamps."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 45, 0, tzinfo=UTC)

        duration_ms = handler.calculate_duration(start, end)

        assert duration_ms == 45 * 60 * 1000  # 45 minutes in ms

    def test_calculate_duration_negative_raises(self) -> None:
        """Test that negative duration raises error."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(MagicMock())

        start = datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="cannot be negative"):
            handler.calculate_duration(start, end)


class TestQueryDuration:
    """Tests for querying duration of activities."""

    def test_query_duration_finds_matching_activity(self) -> None:
        """Test querying duration for a known activity."""
        from ara.storage.models import ActivityDTO, ActivityStatus
        from ara.storage.queries import TimeQueryHandler

        # Mock activity repository
        mock_activity_repo = MagicMock()
        mock_activity_repo.get_by_name.return_value = [
            ActivityDTO(
                id="activity-1",
                name="shower",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-1",
                start_time=datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC),
                start_text="taking a shower",
                pairing_score=0.9,
                duration_ms=900000,  # 15 minutes
            )
        ]

        mock_storage = MagicMock()
        mock_storage.activities = mock_activity_repo

        handler = TimeQueryHandler(mock_storage)
        result = handler.query_duration("shower")

        assert result.success is True
        assert result.duration_ms == 900000
        assert "15 minutes" in result.response_text

    def test_query_duration_no_matching_activity(self) -> None:
        """Test querying duration when no activity found."""
        from ara.storage.queries import TimeQueryHandler

        mock_activity_repo = MagicMock()
        mock_activity_repo.get_by_name.return_value = []

        mock_storage = MagicMock()
        mock_storage.activities = mock_activity_repo

        handler = TimeQueryHandler(mock_storage)
        result = handler.query_duration("nonexistent")

        assert result.success is False
        assert "couldn't find" in result.response_text.lower()

    def test_query_duration_activity_in_progress(self) -> None:
        """Test querying duration for an in-progress activity."""
        from ara.storage.models import ActivityDTO, ActivityStatus
        from ara.storage.queries import TimeQueryHandler

        mock_activity_repo = MagicMock()
        mock_activity_repo.get_by_name.return_value = [
            ActivityDTO(
                name="workout",
                status=ActivityStatus.IN_PROGRESS,
                start_event_id="event-1",
                start_time=datetime.now(UTC) - timedelta(minutes=30),
                start_text="starting workout",
                pairing_score=0.9,
            )
        ]

        mock_storage = MagicMock()
        mock_storage.activities = mock_activity_repo

        handler = TimeQueryHandler(mock_storage)
        result = handler.query_duration("workout")

        assert result.success is True
        assert "still in progress" in result.response_text.lower()

    def test_query_duration_multiple_activities_uses_most_recent(self) -> None:
        """Test that most recent activity is used when multiple match."""
        from ara.storage.models import ActivityDTO, ActivityStatus
        from ara.storage.queries import TimeQueryHandler

        mock_activity_repo = MagicMock()
        # Repository returns most recent first (sorted by start_time DESC)
        mock_activity_repo.get_by_name.return_value = [
            ActivityDTO(
                name="shower",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-2",
                start_time=datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC),
                start_text="taking a shower",
                pairing_score=0.9,
                duration_ms=600000,  # 10 minutes (most recent)
            ),
            ActivityDTO(
                name="shower",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-1",
                start_time=datetime(2024, 1, 14, 8, 0, 0, tzinfo=UTC),
                start_text="taking a shower",
                pairing_score=0.9,
                duration_ms=900000,  # 15 minutes (older)
            ),
        ]

        mock_storage = MagicMock()
        mock_storage.activities = mock_activity_repo

        handler = TimeQueryHandler(mock_storage)
        result = handler.query_duration("shower")

        assert result.success is True
        assert result.duration_ms == 600000  # Uses most recent


class TestQueryAroundTime:
    """Tests for querying activities around a time point."""

    def test_query_around_time_returns_events(self) -> None:
        """Test querying events around a time point."""
        from ara.storage.models import EventDTO, EventType
        from ara.storage.queries import TimeQueryHandler

        mock_event_repo = MagicMock()
        mock_event_repo.get_around_time.return_value = [
            EventDTO(
                id="event-1",
                interaction_id="int-1",
                timestamp=datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC),
                event_type=EventType.ACTIVITY_START,
                context="shower",
                source_text="taking a shower",
                extraction_confidence=0.9,
            ),
            EventDTO(
                id="event-2",
                interaction_id="int-2",
                timestamp=datetime(2024, 1, 15, 10, 20, 0, tzinfo=UTC),
                event_type=EventType.ACTIVITY_END,
                context="shower",
                source_text="finished shower",
                extraction_confidence=0.9,
            ),
        ]

        mock_storage = MagicMock()
        mock_storage.events = mock_event_repo

        handler = TimeQueryHandler(mock_storage)
        time_point = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        result = handler.query_around_time(time_point)

        assert result.success is True
        assert len(result.events_found) == 2

    def test_query_around_time_no_events(self) -> None:
        """Test querying around a time with no events."""
        from ara.storage.queries import TimeQueryHandler

        mock_event_repo = MagicMock()
        mock_event_repo.get_around_time.return_value = []

        mock_storage = MagicMock()
        mock_storage.events = mock_event_repo

        handler = TimeQueryHandler(mock_storage)
        time_point = datetime(2024, 1, 15, 3, 0, 0, tzinfo=UTC)
        result = handler.query_around_time(time_point)

        assert result.success is True  # Still success, just no results
        assert "anything recorded" in result.response_text.lower()


class TestQueryRange:
    """Tests for querying events in a time range."""

    def test_query_range_returns_events(self) -> None:
        """Test querying events in a time range."""
        from ara.storage.models import EventDTO, EventType
        from ara.storage.queries import TimeQueryHandler

        mock_event_repo = MagicMock()
        mock_event_repo.get_in_range.return_value = [
            EventDTO(
                id="event-1",
                interaction_id="int-1",
                timestamp=datetime(2024, 1, 15, 9, 30, 0, tzinfo=UTC),
                event_type=EventType.NOTE,
                context="meeting notes",
                source_text="taking notes",
                extraction_confidence=0.9,
            ),
        ]

        mock_storage = MagicMock()
        mock_storage.events = mock_event_repo

        handler = TimeQueryHandler(mock_storage)
        start = datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        result = handler.query_range(start, end)

        assert result.success is True
        assert len(result.events_found) == 1

    def test_query_range_invalid_range_raises(self) -> None:
        """Test that invalid range raises error."""
        from ara.storage.queries import TimeQueryHandler

        mock_storage = MagicMock()
        handler = TimeQueryHandler(mock_storage)

        start = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 9, 0, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="must be before"):
            handler.query_range(start, end)
