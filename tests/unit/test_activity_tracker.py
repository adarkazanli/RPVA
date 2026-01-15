"""Unit tests for activity tracker.

Tests start/stop tracking with duration calculation.
"""

from datetime import UTC, datetime, timedelta

import pytest

from ara.activities import Activity, ActivityStatus, ActivityTracker, StartResult, StopResult
from ara.notes.models import Category


class TestActivityTracker:
    """Test activity tracking functionality."""

    @pytest.fixture
    def tracker(self) -> ActivityTracker:
        """Create tracker without repository (in-memory mode)."""
        return ActivityTracker(user_id="test-user")

    def test_start_activity(self, tracker: ActivityTracker) -> None:
        """Test starting an activity."""
        result = tracker.start("workout")

        assert isinstance(result, StartResult)
        assert result.activity.name == "workout"
        assert result.activity.status == ActivityStatus.ACTIVE
        assert result.activity.category == Category.HEALTH
        assert result.previous_activity is None
        assert "Started tracking workout" in result.message

    def test_start_auto_categorizes(self, tracker: ActivityTracker) -> None:
        """Test activities are auto-categorized."""
        # Health category
        result = tracker.start("gym session")
        assert result.activity.category == Category.HEALTH

        # Reset
        tracker._active_activity = None

        # Work category
        result = tracker.start("team meeting")
        assert result.activity.category == Category.WORK

    def test_start_closes_previous(self, tracker: ActivityTracker) -> None:
        """Test starting new activity auto-closes previous."""
        # Start first activity
        tracker.start("reading")

        # Start second activity
        result = tracker.start("cooking")

        assert result.previous_activity is not None
        assert result.previous_activity.name == "reading"
        assert result.previous_activity.status == ActivityStatus.COMPLETED
        assert result.activity.name == "cooking"
        assert result.activity.status == ActivityStatus.ACTIVE

    def test_stop_activity(self, tracker: ActivityTracker) -> None:
        """Test stopping an activity."""
        tracker.start("workout")

        result = tracker.stop()

        assert isinstance(result, StopResult)
        assert result.activity.name == "workout"
        assert result.activity.status == ActivityStatus.COMPLETED
        assert result.activity.duration_minutes is not None
        assert "Stopped workout" in result.message

    def test_stop_by_name(self, tracker: ActivityTracker) -> None:
        """Test stopping activity by name."""
        tracker.start("workout")

        result = tracker.stop("workout")

        assert result.activity.name == "workout"
        assert result.activity.status == ActivityStatus.COMPLETED

    def test_stop_no_activity_raises(self, tracker: ActivityTracker) -> None:
        """Test stopping when no activity raises error."""
        with pytest.raises(ValueError, match="No active activity"):
            tracker.stop()

    def test_stop_wrong_name_raises(self, tracker: ActivityTracker) -> None:
        """Test stopping wrong activity name raises error."""
        tracker.start("workout")

        with pytest.raises(ValueError, match="No active activity matching"):
            tracker.stop("meeting")

    def test_get_active(self, tracker: ActivityTracker) -> None:
        """Test getting active activity."""
        assert tracker.get_active() is None

        tracker.start("workout")
        active = tracker.get_active()

        assert active is not None
        assert active.name == "workout"
        assert active.status == ActivityStatus.ACTIVE

    def test_get_active_after_stop(self, tracker: ActivityTracker) -> None:
        """Test get_active returns None after stop."""
        tracker.start("workout")
        tracker.stop()

        assert tracker.get_active() is None


class TestActivity:
    """Test Activity model."""

    def test_complete_calculates_duration(self) -> None:
        """Test complete() calculates duration correctly."""
        start = datetime.now(UTC) - timedelta(minutes=30)
        activity = Activity(
            name="test",
            category=Category.WORK,
            start_time=start,
        )

        activity.complete()

        assert activity.status == ActivityStatus.COMPLETED
        assert activity.end_time is not None
        assert activity.duration_minutes == 30

    def test_complete_with_end_time(self) -> None:
        """Test complete() with explicit end time."""
        start = datetime.now(UTC)
        end = start + timedelta(hours=1, minutes=15)

        activity = Activity(
            name="test",
            category=Category.WORK,
            start_time=start,
        )
        activity.complete(end_time=end)

        assert activity.duration_minutes == 75

    def test_complete_auto_closed(self) -> None:
        """Test complete() with auto_closed flag."""
        activity = Activity(
            name="test",
            category=Category.WORK,
        )
        activity.complete(auto_closed=True)

        assert activity.auto_closed is True

    def test_to_dict(self) -> None:
        """Test serialization to dict."""
        activity = Activity(
            name="workout",
            category=Category.HEALTH,
            user_id="test-user",
        )

        data = activity.to_dict()

        assert data["name"] == "workout"
        assert data["category"] == "health"
        assert data["status"] == "active"
        assert data["user_id"] == "test-user"

    def test_from_dict(self) -> None:
        """Test deserialization from dict."""
        data = {
            "_id": "test-id",
            "name": "workout",
            "category": "health",
            "start_time": datetime.now(UTC),
            "status": "completed",
            "duration_minutes": 45,
            "user_id": "test-user",
        }

        activity = Activity.from_dict(data)

        assert activity.id == "test-id"
        assert activity.name == "workout"
        assert activity.category == Category.HEALTH
        assert activity.status == ActivityStatus.COMPLETED
        assert activity.duration_minutes == 45
