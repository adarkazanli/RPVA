"""Data models for activity tracking.

Defines Activity entity and ActivityStatus enum.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

# Import Category from notes module for consistency
from ara.notes.models import Category


class ActivityStatus(Enum):
    """Status of a time-tracked activity."""

    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class Activity:
    """A time-tracked activity with duration.

    Attributes:
        name: Activity name (e.g., "workout")
        category: Auto-assigned category
        start_time: When activity started
        status: Active or completed
        user_id: User identifier
        id: MongoDB document ID
        end_time: When activity ended (None if active)
        duration_minutes: Calculated duration (None if active)
        auto_closed: True if closed by timeout
    """

    name: str
    category: Category
    start_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    status: ActivityStatus = ActivityStatus.ACTIVE
    user_id: str = "default"
    id: str | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = None
    auto_closed: bool = False

    def complete(self, end_time: datetime | None = None, auto_closed: bool = False) -> None:
        """Mark the activity as completed.

        Args:
            end_time: When activity ended (defaults to now)
            auto_closed: Whether this was auto-closed by timeout
        """
        self.end_time = end_time or datetime.now(UTC)
        self.status = ActivityStatus.COMPLETED
        self.auto_closed = auto_closed

        # Calculate duration in minutes
        delta = self.end_time - self.start_time
        self.duration_minutes = int(delta.total_seconds() / 60)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "name": self.name,
            "category": self.category.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_minutes": self.duration_minutes,
            "status": self.status.value,
            "auto_closed": self.auto_closed,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Activity":
        """Create from MongoDB document."""
        start_time = data.get("start_time", datetime.now(UTC))
        end_time = data.get("end_time")

        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        if end_time and end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=UTC)

        return cls(
            id=str(data.get("_id", "")) if data.get("_id") else None,
            name=data.get("name", ""),
            category=Category(data.get("category", "uncategorized")),
            start_time=start_time,
            end_time=end_time,
            duration_minutes=data.get("duration_minutes"),
            status=ActivityStatus(data.get("status", "active")),
            auto_closed=data.get("auto_closed", False),
            user_id=data.get("user_id", "default"),
        )


__all__ = ["Activity", "ActivityStatus", "Category"]
