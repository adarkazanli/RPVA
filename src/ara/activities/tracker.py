"""Activity tracker for time tracking.

Provides start/stop tracking with duration calculation.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from ara.notes.categorizer import categorize

from .models import Activity, ActivityStatus, Category

logger = logging.getLogger(__name__)


@dataclass
class StartResult:
    """Result of starting an activity."""

    activity: Activity
    previous_activity: Activity | None  # Auto-closed activity, if any
    message: str  # Confirmation message for TTS


@dataclass
class StopResult:
    """Result of stopping an activity."""

    activity: Activity
    message: str  # Confirmation message for TTS


class ActivityRepository(Protocol):
    """Protocol for activity persistence."""

    def insert(self, activity: dict[str, Any]) -> str:
        """Insert activity and return ID."""
        ...

    def update(self, activity_id: str, data: dict[str, Any]) -> None:
        """Update activity by ID."""
        ...

    def find_active(self, user_id: str) -> dict[str, Any] | None:
        """Find active activity for user."""
        ...

    def find_today(self, user_id: str) -> list[dict[str, Any]]:
        """Find today's activities for user."""
        ...

    def find_by_date_range(
        self, user_id: str, start: datetime, end: datetime, category: str | None = None
    ) -> list[dict[str, Any]]:
        """Find activities in date range."""
        ...


class ActivityTracker:
    """Tracks activity durations via start/stop commands.

    Enforces single active activity constraint.
    """

    def __init__(
        self,
        repository: ActivityRepository | None = None,
        user_id: str = "default",
    ) -> None:
        """Initialize tracker.

        Args:
            repository: Optional repository for persistence
            user_id: Default user ID for activities
        """
        self._repository = repository
        self._user_id = user_id
        # In-memory tracking when no repository
        self._active_activity: Activity | None = None

    def start(self, activity_name: str) -> StartResult:
        """Start tracking a new activity.

        If another activity is active, it will be auto-closed first.

        Args:
            activity_name: Name of the activity (e.g., "workout")

        Returns:
            StartResult with new activity and optional closed activity
        """
        previous: Activity | None = None

        # Check for existing active activity
        current = self.get_active()
        if current:
            # Auto-close the current activity
            current.complete()
            previous = current
            logger.info(f"Auto-closed activity '{current.name}' ({current.duration_minutes} min)")

            # Persist if repository available
            if self._repository and current.id:
                self._repository.update(current.id, current.to_dict())

        # Create new activity with auto-categorization
        category = categorize(activity_name)
        activity = Activity(
            name=activity_name,
            category=category,
            start_time=datetime.now(UTC),
            status=ActivityStatus.ACTIVE,
            user_id=self._user_id,
        )

        # Persist if repository available
        if self._repository:
            activity_id = self._repository.insert(activity.to_dict())
            activity.id = activity_id
        else:
            # In-memory tracking
            self._active_activity = activity

        logger.info(f"Started activity '{activity_name}' (category: {category.value})")

        # Build confirmation message
        if previous:
            message = f"Stopped {previous.name} ({previous.duration_minutes} minutes). Started tracking {activity_name}!"
        else:
            message = f"Started tracking {activity_name}!"

        return StartResult(
            activity=activity,
            previous_activity=previous,
            message=message,
        )

    def stop(self, activity_name: str | None = None) -> StopResult:
        """Stop the current or named activity.

        Args:
            activity_name: Optional name to match. If None, stops current active.

        Returns:
            StopResult with completed activity and duration

        Raises:
            ValueError: If no matching activity is active
        """
        current = self.get_active()

        if not current:
            raise ValueError("No active activity to stop")

        # If name specified, check if it matches
        if activity_name and activity_name.lower() not in current.name.lower():
            raise ValueError(f"No active activity matching '{activity_name}'")

        # Complete the activity
        current.complete()

        # Persist if repository available
        if self._repository and current.id:
            self._repository.update(current.id, current.to_dict())
        else:
            # Clear in-memory tracking
            self._active_activity = None

        logger.info(f"Stopped activity '{current.name}' ({current.duration_minutes} minutes)")

        # Build confirmation message
        message = f"Stopped {current.name}. {current.duration_minutes} minutes total."

        return StopResult(
            activity=current,
            message=message,
        )

    def get_active(self) -> Activity | None:
        """Get the currently active activity.

        Returns:
            Current active activity, or None if none active
        """
        if self._repository:
            doc = self._repository.find_active(self._user_id)
            if doc:
                return Activity.from_dict(doc)
            return None
        return self._active_activity

    def get_today(self) -> list[Activity]:
        """Get all activities from today.

        Returns:
            List of today's activities, most recent first
        """
        if not self._repository:
            activities = []
            if self._active_activity:
                activities.append(self._active_activity)
            return activities

        docs = self._repository.find_today(self._user_id)
        return [Activity.from_dict(doc) for doc in docs]

    def get_by_date_range(
        self,
        start: datetime,
        end: datetime,
        category: Category | None = None,
    ) -> list[Activity]:
        """Get activities within a date range.

        Args:
            start: Range start (inclusive)
            end: Range end (inclusive)
            category: Optional category filter

        Returns:
            List of matching activities
        """
        if not self._repository:
            return []

        category_str = category.value if category else None
        docs = self._repository.find_by_date_range(self._user_id, start, end, category_str)
        return [Activity.from_dict(doc) for doc in docs]


__all__ = ["ActivityTracker", "ActivityRepository", "StartResult", "StopResult"]
