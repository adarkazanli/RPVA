"""Data models for note-taking.

Defines Note entity and Category enum for note classification.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class Category(Enum):
    """Fixed categories for notes and activities."""

    WORK = "work"
    PERSONAL = "personal"
    HEALTH = "health"
    ERRANDS = "errands"
    UNCATEGORIZED = "uncategorized"


@dataclass
class Note:
    """A captured voice note with extracted entities.

    Attributes:
        transcript: Raw voice transcript
        category: Auto-assigned category
        timestamp: When the note was captured
        people: Extracted person names
        topics: Extracted subject matter
        locations: Extracted place references
        activity_id: Associated activity (if any)
        user_id: User identifier
        id: MongoDB document ID
    """

    transcript: str
    category: Category
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    people: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    activity_id: str | None = None
    user_id: str = "default"
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "transcript": self.transcript,
            "category": self.category.value,
            "timestamp": self.timestamp,
            "people": self.people,
            "topics": self.topics,
            "locations": self.locations,
            "activity_id": self.activity_id,
            "user_id": self.user_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Note":
        """Create from MongoDB document."""
        timestamp = data.get("timestamp", datetime.now(UTC))
        if timestamp and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        return cls(
            id=str(data.get("_id", "")) if data.get("_id") else None,
            transcript=data.get("transcript", ""),
            category=Category(data.get("category", "uncategorized")),
            timestamp=timestamp,
            people=data.get("people", []),
            topics=data.get("topics", []),
            locations=data.get("locations", []),
            activity_id=data.get("activity_id"),
            user_id=data.get("user_id", "default"),
        )


__all__ = ["Category", "Note"]
