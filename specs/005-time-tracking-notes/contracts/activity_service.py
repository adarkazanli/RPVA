"""Activity Service Contract.

Defines the interface for activity time tracking.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class ActivityResult:
    """Result of an activity operation."""

    id: str
    name: str
    category: str
    start_time: datetime
    end_time: datetime | None
    duration_minutes: int | None
    status: str  # "active" | "completed"


@dataclass
class StartResult:
    """Result of starting an activity."""

    activity: ActivityResult
    previous_activity: ActivityResult | None  # Auto-closed activity, if any
    message: str  # Confirmation message for TTS


@dataclass
class StopResult:
    """Result of stopping an activity."""

    activity: ActivityResult
    message: str  # Confirmation message for TTS


class ActivityTracker(Protocol):
    """Interface for tracking activity durations."""

    def start(self, activity_name: str) -> StartResult:
        """Start tracking a new activity.

        If another activity is active, it will be auto-closed first.

        Args:
            activity_name: Name of the activity (e.g., "workout")

        Returns:
            StartResult with new activity and optional closed activity

        Performance:
            Must complete in <1 second
        """
        ...

    def stop(self, activity_name: str | None = None) -> StopResult:
        """Stop the current or named activity.

        Args:
            activity_name: Optional name to match. If None, stops current active.

        Returns:
            StopResult with completed activity and duration

        Raises:
            ValueError: If no matching activity is active

        Performance:
            Must complete in <1 second
        """
        ...

    def get_active(self) -> ActivityResult | None:
        """Get the currently active activity.

        Returns:
            Current active activity, or None if none active
        """
        ...

    def get_today(self) -> list[ActivityResult]:
        """Get all activities from today.

        Returns:
            List of today's activities, most recent first
        """
        ...

    def get_by_date_range(
        self,
        start: datetime,
        end: datetime,
        category: str | None = None,
    ) -> list[ActivityResult]:
        """Get activities within a date range.

        Args:
            start: Range start (inclusive)
            end: Range end (inclusive)
            category: Optional category filter

        Returns:
            List of matching activities
        """
        ...


class ActivityTimeout(Protocol):
    """Interface for auto-closing stale activities."""

    def check_and_close_stale(self, timeout_hours: float = 4.0) -> list[ActivityResult]:
        """Check for and auto-close activities exceeding timeout.

        Args:
            timeout_hours: Hours after which to auto-close (default: 4)

        Returns:
            List of activities that were auto-closed
        """
        ...
