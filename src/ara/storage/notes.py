"""Note and TimeTracking repositories for MongoDB storage.

Handles storage for voice notes and activity time tracking.
"""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.collection import Collection

from .client import retry_on_connection_failure
from .models import NoteDTO, TimeTrackingActivityDTO

logger = logging.getLogger(__name__)


class NoteRepository:
    """Repository for note storage operations."""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        """Initialize repository with MongoDB collection.

        Args:
            collection: MongoDB collection for notes.
        """
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._collection.create_index([("timestamp", DESCENDING)])
        self._collection.create_index([("user_id", 1), ("timestamp", DESCENDING)])
        self._collection.create_index([("category", 1), ("timestamp", DESCENDING)])
        self._collection.create_index([("people", 1)])
        self._collection.create_index([("topics", 1)])
        self._collection.create_index([("locations", 1)])
        # Text index for full-text search
        self._collection.create_index([("transcript", "text")])

    @retry_on_connection_failure()
    def save(self, note: NoteDTO) -> str:
        """Save a note and return its ID.

        Args:
            note: The note to save.

        Returns:
            The generated document ID.
        """
        doc = note.to_dict()
        doc["created_at"] = datetime.now(UTC)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    @retry_on_connection_failure()
    def get_by_id(self, note_id: str) -> NoteDTO | None:
        """Retrieve a note by ID.

        Args:
            note_id: The note ID.

        Returns:
            The note or None if not found.
        """
        from bson import ObjectId

        try:
            doc = self._collection.find_one({"_id": ObjectId(note_id)})
        except Exception:
            return None

        if doc is None:
            return None
        return NoteDTO.from_dict(doc)

    @retry_on_connection_failure()
    def find_by_person(
        self, person: str, user_id: str = "default", limit: int = 10
    ) -> list[NoteDTO]:
        """Find notes mentioning a person.

        Args:
            person: Person name to search for (case-insensitive).
            user_id: User ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of matching notes, most recent first.
        """
        import re

        pattern = re.compile(person, re.IGNORECASE)
        cursor = (
            self._collection.find({"user_id": user_id, "people": pattern})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return [NoteDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def find_by_topic(
        self, topic: str, user_id: str = "default", limit: int = 10
    ) -> list[NoteDTO]:
        """Find notes about a topic.

        Args:
            topic: Topic to search for (case-insensitive).
            user_id: User ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of matching notes, most recent first.
        """
        import re

        pattern = re.compile(topic, re.IGNORECASE)
        cursor = (
            self._collection.find({"user_id": user_id, "topics": pattern})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return [NoteDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def search_text(
        self, query: str, user_id: str = "default", limit: int = 10
    ) -> list[NoteDTO]:
        """Full-text search in note transcripts.

        Args:
            query: Search query.
            user_id: User ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of matching notes.
        """
        cursor = (
            self._collection.find(
                {"user_id": user_id, "$text": {"$search": query}},
                {"score": {"$meta": "textScore"}},
            )
            .sort([("score", {"$meta": "textScore"})])
            .limit(limit)
        )
        return [NoteDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_recent(self, user_id: str = "default", limit: int = 10) -> list[NoteDTO]:
        """Get most recent notes for a user.

        Args:
            user_id: User ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of notes, most recent first.
        """
        cursor = (
            self._collection.find({"user_id": user_id})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )
        return [NoteDTO.from_dict(doc) for doc in cursor]


class TimeTrackingActivityRepository:
    """Repository for time-tracked activities."""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        """Initialize repository with MongoDB collection.

        Args:
            collection: MongoDB collection for activities.
        """
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._collection.create_index([("start_time", DESCENDING)])
        self._collection.create_index([("user_id", 1), ("status", 1)])
        self._collection.create_index([("user_id", 1), ("start_time", DESCENDING)])
        self._collection.create_index([("category", 1), ("start_time", DESCENDING)])

    @retry_on_connection_failure()
    def save(self, activity: TimeTrackingActivityDTO) -> str:
        """Save an activity and return its ID.

        Args:
            activity: The activity to save.

        Returns:
            The generated document ID.
        """
        doc = activity.to_dict()
        doc["created_at"] = datetime.now(UTC)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    @retry_on_connection_failure()
    def update(self, activity: TimeTrackingActivityDTO) -> bool:
        """Update an existing activity.

        Args:
            activity: The activity to update (must have id set).

        Returns:
            True if updated, False if not found.
        """
        from bson import ObjectId

        if not activity.id:
            return False

        doc = activity.to_dict()
        doc["updated_at"] = datetime.now(UTC)

        result = self._collection.update_one(
            {"_id": ObjectId(activity.id)}, {"$set": doc}
        )
        return result.modified_count > 0

    @retry_on_connection_failure()
    def get_by_id(self, activity_id: str) -> TimeTrackingActivityDTO | None:
        """Retrieve an activity by ID.

        Args:
            activity_id: The activity ID.

        Returns:
            The activity or None if not found.
        """
        from bson import ObjectId

        try:
            doc = self._collection.find_one({"_id": ObjectId(activity_id)})
        except Exception:
            return None

        if doc is None:
            return None
        return TimeTrackingActivityDTO.from_dict(doc)

    @retry_on_connection_failure()
    def get_active(self, user_id: str = "default") -> TimeTrackingActivityDTO | None:
        """Get the currently active activity for a user.

        Args:
            user_id: User ID to filter by.

        Returns:
            The active activity or None.
        """
        doc = self._collection.find_one(
            {"user_id": user_id, "status": "active"},
            sort=[("start_time", DESCENDING)],
        )
        if doc is None:
            return None
        return TimeTrackingActivityDTO.from_dict(doc)

    @retry_on_connection_failure()
    def get_for_date(
        self, target_date: date, user_id: str = "default"
    ) -> list[TimeTrackingActivityDTO]:
        """Get all activities for a specific date.

        Args:
            target_date: The date to query.
            user_id: User ID to filter by.

        Returns:
            List of activities for that date.
        """
        start_of_day = datetime.combine(target_date, datetime.min.time(), tzinfo=UTC)
        end_of_day = start_of_day + timedelta(days=1)

        cursor = self._collection.find(
            {
                "user_id": user_id,
                "start_time": {"$gte": start_of_day, "$lt": end_of_day},
            }
        ).sort("start_time", ASCENDING)

        return [TimeTrackingActivityDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_for_date_range(
        self, start_date: date, end_date: date, user_id: str = "default"
    ) -> list[TimeTrackingActivityDTO]:
        """Get all activities in a date range.

        Args:
            start_date: Start of range (inclusive).
            end_date: End of range (inclusive).
            user_id: User ID to filter by.

        Returns:
            List of activities in the range.
        """
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=UTC)

        cursor = self._collection.find(
            {
                "user_id": user_id,
                "start_time": {"$gte": start_dt, "$lte": end_dt},
            }
        ).sort("start_time", ASCENDING)

        return [TimeTrackingActivityDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_by_category(
        self, category: str, user_id: str = "default", limit: int = 50
    ) -> list[TimeTrackingActivityDTO]:
        """Get activities by category.

        Args:
            category: Category to filter by.
            user_id: User ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of activities, most recent first.
        """
        cursor = (
            self._collection.find({"user_id": user_id, "category": category})
            .sort("start_time", DESCENDING)
            .limit(limit)
        )
        return [TimeTrackingActivityDTO.from_dict(doc) for doc in cursor]


class MongoActivityDataSource:
    """Adapter for digest generators to use MongoDB data.

    Implements the ActivityDataSource protocol expected by
    DailyDigestGenerator and WeeklyDigestGenerator.
    """

    def __init__(self, repository: TimeTrackingActivityRepository) -> None:
        """Initialize with activity repository.

        Args:
            repository: The TimeTrackingActivityRepository to use.
        """
        self._repository = repository

    def get_activities_for_date(
        self, target_date: date, user_id: str
    ) -> list[dict[str, Any]]:
        """Get activities for a specific date as dicts.

        Args:
            target_date: The date to query.
            user_id: User ID to filter by.

        Returns:
            List of activity dicts for digest processing.
        """
        activities = self._repository.get_for_date(target_date, user_id)
        return [
            {
                "name": a.name,
                "category": a.category,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "duration_minutes": a.duration_minutes or 0,
                "status": a.status,
            }
            for a in activities
        ]

    def get_activities_for_date_range(
        self, start_date: date, end_date: date, user_id: str
    ) -> list[dict[str, Any]]:
        """Get activities for a date range as dicts.

        Args:
            start_date: Start of range (inclusive).
            end_date: End of range (inclusive).
            user_id: User ID to filter by.

        Returns:
            List of activity dicts for digest processing.
        """
        activities = self._repository.get_for_date_range(start_date, end_date, user_id)
        return [
            {
                "name": a.name,
                "category": a.category,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "duration_minutes": a.duration_minutes or 0,
                "status": a.status,
            }
            for a in activities
        ]


__all__ = [
    "NoteRepository",
    "TimeTrackingActivityRepository",
    "MongoActivityDataSource",
]
