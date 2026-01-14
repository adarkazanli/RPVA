"""Event and Activity repositories for MongoDB storage.

Handles event extraction, storage, and activity pairing.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from pymongo import DESCENDING
from pymongo.collection import Collection

from .client import retry_on_connection_failure
from .models import ActivityDTO, ActivityStatus, EventDTO, EventType

logger = logging.getLogger(__name__)


class EventRepository:
    """Repository for event storage operations."""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        """Initialize repository with MongoDB collection.

        Args:
            collection: MongoDB collection for events.
        """
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._collection.create_index([("timestamp", DESCENDING)])
        self._collection.create_index([("type", 1), ("timestamp", DESCENDING)])
        self._collection.create_index([("context", 1), ("timestamp", DESCENDING)])
        self._collection.create_index("linked_event_id")
        self._collection.create_index("activity_id")

    @retry_on_connection_failure()
    def save(self, event: EventDTO) -> str:
        """Save an event and return its ID.

        Args:
            event: The event to save.

        Returns:
            The generated document ID.
        """
        doc = event.to_dict()
        doc["created_at"] = datetime.now(UTC)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    @retry_on_connection_failure()
    def get_by_id(self, event_id: str) -> EventDTO | None:
        """Retrieve an event by ID.

        Args:
            event_id: The event ID.

        Returns:
            The event or None if not found.
        """
        from bson import ObjectId

        try:
            doc = self._collection.find_one({"_id": ObjectId(event_id)})
        except Exception:
            return None

        if doc is None:
            return None
        return EventDTO.from_dict(doc)

    @retry_on_connection_failure()
    def get_by_type(self, event_type: EventType, limit: int = 50) -> list[EventDTO]:
        """Get events by type.

        Args:
            event_type: The event type to filter by.
            limit: Maximum number to return.

        Returns:
            List of events, most recent first.
        """
        cursor = (
            self._collection.find({"type": event_type.value})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        return [EventDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_around_time(
        self,
        time_point: datetime,
        window_minutes: int = 15,
    ) -> list[EventDTO]:
        """Get events around a specific time point.

        Args:
            time_point: The center time point.
            window_minutes: Minutes before and after to include.

        Returns:
            List of events within the time window.
        """
        window = timedelta(minutes=window_minutes)
        start = time_point - window
        end = time_point + window

        cursor = self._collection.find({"timestamp": {"$gte": start, "$lte": end}}).sort(
            "timestamp", 1
        )

        return [EventDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_in_range(self, start: datetime, end: datetime) -> list[EventDTO]:
        """Get events within a time range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            List of events in the range.
        """
        cursor = self._collection.find({"timestamp": {"$gte": start, "$lte": end}}).sort(
            "timestamp", 1
        )

        return [EventDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def find_unlinked_start_events(
        self,
        context: str,  # noqa: ARG002 - reserved for future context-based filtering
        max_age_hours: int = 4,
    ) -> list[EventDTO]:
        """Find unlinked activity_start events for pairing.

        Args:
            context: The context/activity description to match.
            max_age_hours: Maximum hours ago to search.

        Returns:
            List of candidate start events.
        """
        cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)

        cursor = self._collection.find(
            {
                "type": EventType.ACTIVITY_START.value,
                "linked_event_id": None,
                "timestamp": {"$gte": cutoff},
            }
        ).sort("timestamp", DESCENDING)

        return [EventDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def link_events(self, start_id: str, end_id: str) -> None:
        """Link two events as a start/end pair.

        Args:
            start_id: The start event ID.
            end_id: The end event ID.
        """
        from bson import ObjectId

        # Update start event to link to end
        self._collection.update_one(
            {"_id": ObjectId(start_id)},
            {"$set": {"linked_event_id": end_id}},
        )

        # Update end event to link to start
        self._collection.update_one(
            {"_id": ObjectId(end_id)},
            {"$set": {"linked_event_id": start_id}},
        )

    @retry_on_connection_failure()
    def set_activity_id(self, event_id: str, activity_id: str) -> None:
        """Set the activity ID for an event.

        Args:
            event_id: The event ID.
            activity_id: The activity ID to set.
        """
        from bson import ObjectId

        self._collection.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"activity_id": activity_id}},
        )

    @retry_on_connection_failure()
    def get_recent(self, limit: int = 50) -> list[EventDTO]:
        """Get recent events.

        Args:
            limit: Maximum number to return.

        Returns:
            List of events, most recent first.
        """
        cursor = self._collection.find().sort("timestamp", DESCENDING).limit(limit)
        return [EventDTO.from_dict(doc) for doc in cursor]


class ActivityRepository:
    """Repository for activity storage operations."""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        """Initialize repository with MongoDB collection.

        Args:
            collection: MongoDB collection for activities.
        """
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._collection.create_index([("status", 1), ("start_time", DESCENDING)])
        self._collection.create_index([("name", 1), ("start_time", DESCENDING)])
        self._collection.create_index([("end_time", DESCENDING)])

    @retry_on_connection_failure()
    def save(self, activity: ActivityDTO) -> str:
        """Save an activity and return its ID.

        Args:
            activity: The activity to save.

        Returns:
            The generated document ID.
        """
        doc = activity.to_dict()
        doc["created_at"] = datetime.now(UTC)
        doc["updated_at"] = datetime.now(UTC)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    @retry_on_connection_failure()
    def get_by_id(self, activity_id: str) -> ActivityDTO | None:
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
        return ActivityDTO.from_dict(doc)

    @retry_on_connection_failure()
    def get_in_progress(self) -> list[ActivityDTO]:
        """Get all in-progress activities.

        Returns:
            List of activities with status IN_PROGRESS.
        """
        cursor = self._collection.find({"status": ActivityStatus.IN_PROGRESS.value}).sort(
            "start_time", DESCENDING
        )

        return [ActivityDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def complete(
        self,
        activity_id: str,
        end_event_id: str,
        end_time: datetime,
        end_text: str | None = None,
    ) -> ActivityDTO | None:
        """Mark an activity as completed.

        Args:
            activity_id: The activity ID.
            end_event_id: The end event ID.
            end_time: The end timestamp.
            end_text: Optional end text from transcript.

        Returns:
            The updated activity with duration calculated, or None if not found.
        """
        from bson import ObjectId

        # Get current activity to calculate duration
        activity = self.get_by_id(activity_id)
        if activity is None:
            return None

        duration_ms = int((end_time - activity.start_time).total_seconds() * 1000)

        update_doc: dict[str, Any] = {
            "status": ActivityStatus.COMPLETED.value,
            "end_event_id": end_event_id,
            "end_time": end_time,
            "duration_ms": duration_ms,
            "updated_at": datetime.now(UTC),
        }

        if end_text:
            update_doc["context.end_text"] = end_text

        self._collection.update_one(
            {"_id": ObjectId(activity_id)},
            {"$set": update_doc},
        )

        # Return updated activity
        return self.get_by_id(activity_id)

    @retry_on_connection_failure()
    def get_by_name(self, name: str, limit: int = 10) -> list[ActivityDTO]:
        """Get activities by name.

        Args:
            name: Activity name to search (case-insensitive partial match).
            limit: Maximum number to return.

        Returns:
            List of matching activities, most recent first.
        """
        import re

        pattern = re.compile(re.escape(name), re.IGNORECASE)
        cursor = (
            self._collection.find({"name": {"$regex": pattern}})
            .sort("start_time", DESCENDING)
            .limit(limit)
        )

        return [ActivityDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def calculate_average_duration(self, name: str) -> int | None:
        """Calculate average duration for an activity type.

        Args:
            name: Activity name.

        Returns:
            Average duration in milliseconds, or None if no data.
        """
        import re

        pattern = re.compile(re.escape(name), re.IGNORECASE)

        pipeline: list[dict[str, Any]] = [
            {
                "$match": {
                    "name": {"$regex": pattern},
                    "status": ActivityStatus.COMPLETED.value,
                    "duration_ms": {"$exists": True, "$ne": None},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "avg_duration": {"$avg": "$duration_ms"},
                }
            },
        ]

        result = list(self._collection.aggregate(pipeline))
        if not result:
            return None

        return int(result[0]["avg_duration"])

    @retry_on_connection_failure()
    def get_recent(self, limit: int = 20) -> list[ActivityDTO]:
        """Get recent activities.

        Args:
            limit: Maximum number to return.

        Returns:
            List of activities, most recent first.
        """
        cursor = self._collection.find().sort("start_time", DESCENDING).limit(limit)
        return [ActivityDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_completed_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[ActivityDTO]:
        """Get completed activities within a time range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            List of completed activities in the range.
        """
        cursor = self._collection.find(
            {
                "status": ActivityStatus.COMPLETED.value,
                "start_time": {"$gte": start, "$lte": end},
            }
        ).sort("start_time", 1)

        return [ActivityDTO.from_dict(doc) for doc in cursor]


__all__ = [
    "EventRepository",
    "ActivityRepository",
]
