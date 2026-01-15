"""Integration tests for activity tracking flow.

Tests end-to-end activity start/stop with duration calculation.
"""

from datetime import UTC, datetime, timedelta

import pytest

from ara.activities import ActivityStatus, ActivityTracker
from ara.notes.models import Category


class TestActivityTrackingFlow:
    """Test complete activity tracking workflow."""

    @pytest.fixture
    def tracker(self) -> ActivityTracker:
        """Create tracker for testing."""
        return ActivityTracker(user_id="test-user")

    def test_start_stop_flow(self, tracker: ActivityTracker) -> None:
        """Test basic start/stop flow."""
        # Start activity
        start_result = tracker.start("morning workout")

        assert start_result.activity.status == ActivityStatus.ACTIVE
        assert start_result.activity.category == Category.HEALTH

        # Stop activity
        stop_result = tracker.stop()

        assert stop_result.activity.status == ActivityStatus.COMPLETED
        assert stop_result.activity.duration_minutes is not None
        assert stop_result.activity.duration_minutes >= 0

    def test_auto_close_flow(self, tracker: ActivityTracker) -> None:
        """Test auto-close when starting new activity."""
        # Start first activity
        tracker.start("reading")

        # Start second activity (should auto-close first)
        result = tracker.start("lunch")

        # Verify first was closed
        assert result.previous_activity is not None
        assert result.previous_activity.name == "reading"
        assert result.previous_activity.status == ActivityStatus.COMPLETED

        # Verify second is active
        assert result.activity.name == "lunch"
        assert result.activity.status == ActivityStatus.ACTIVE

    def test_sequential_activities(self, tracker: ActivityTracker) -> None:
        """Test multiple sequential activities."""
        # Activity 1
        tracker.start("workout")
        result1 = tracker.stop()
        assert result1.activity.name == "workout"

        # Activity 2
        tracker.start("shower")
        result2 = tracker.stop()
        assert result2.activity.name == "shower"

        # Activity 3
        tracker.start("breakfast")
        result3 = tracker.stop()
        assert result3.activity.name == "breakfast"

        # No active activity
        assert tracker.get_active() is None

    def test_category_variety(self, tracker: ActivityTracker) -> None:
        """Test activities get different categories."""
        categories_seen = set()

        # Start and stop various activities
        for activity_name in ["workout", "team meeting", "groceries", "dinner with family"]:
            result = tracker.start(activity_name)
            categories_seen.add(result.activity.category)
            tracker.stop()

        # Should have seen multiple categories
        assert len(categories_seen) >= 3

    def test_stop_with_name_match(self, tracker: ActivityTracker) -> None:
        """Test stopping by partial name match."""
        tracker.start("morning workout routine")

        # Should match partial name
        result = tracker.stop("workout")

        assert result.activity.name == "morning workout routine"
        assert result.activity.status == ActivityStatus.COMPLETED

    def test_duration_calculation(self, tracker: ActivityTracker) -> None:
        """Test duration is calculated on stop."""
        # Manually set start time to test duration
        tracker.start("test")
        activity = tracker.get_active()
        assert activity is not None

        # Manually adjust start time for testing
        activity.start_time = datetime.now(UTC) - timedelta(minutes=15)

        # Stop and check duration
        result = tracker.stop()

        # Duration should be approximately 15 minutes
        assert result.activity.duration_minutes is not None
        assert 14 <= result.activity.duration_minutes <= 16

    def test_message_formatting(self, tracker: ActivityTracker) -> None:
        """Test confirmation messages are well-formatted."""
        # Start message
        start_result = tracker.start("coding")
        assert "Started tracking coding" in start_result.message

        # Stop message
        stop_result = tracker.stop()
        assert "Stopped coding" in stop_result.message
        assert "minutes" in stop_result.message

    def test_auto_close_message(self, tracker: ActivityTracker) -> None:
        """Test auto-close message includes previous activity."""
        tracker.start("reading")
        result = tracker.start("cooking")

        assert "Stopped reading" in result.message
        assert "Started tracking cooking" in result.message
