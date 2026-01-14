"""Storage interface contracts for MongoDB Data Store.

This file defines the abstract interfaces that the storage module must implement.
These contracts serve as the specification for implementation.

Date: 2026-01-14
Feature: MongoDB Data Store for Voice Agent
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Types of events that can be extracted from interactions."""

    ACTIVITY_START = "activity_start"
    ACTIVITY_END = "activity_end"
    NOTE = "note"
    REMINDER = "reminder"
    QUERY = "query"


class ActivityStatus(Enum):
    """Status of an activity (paired start/end events)."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class TimeQueryType(Enum):
    """Types of time-based queries users can make."""

    DURATION = "duration"  # Time between two events
    RANGE_SEARCH = "range_search"  # Events within time range
    POINT_SEARCH = "point_search"  # Events around a time point


# ---------------------------------------------------------------------------
# Data Transfer Objects (DTOs)
# ---------------------------------------------------------------------------


@dataclass
class InteractionDTO:
    """Data transfer object for voice interactions."""

    id: str | None
    session_id: str
    timestamp: datetime
    device_id: str
    transcript: str
    transcript_confidence: float
    intent_type: str
    intent_confidence: float
    entities: dict[str, Any]
    response_text: str
    response_source: str
    latency_ms: dict[str, int]
    events_extracted: list[str]


@dataclass
class EventDTO:
    """Data transfer object for extracted events."""

    id: str | None
    interaction_id: str
    timestamp: datetime
    event_type: EventType
    context: str
    entities: dict[str, Any]
    linked_event_id: str | None
    activity_id: str | None
    source_text: str
    extraction_confidence: float


@dataclass
class ActivityDTO:
    """Data transfer object for paired activities."""

    id: str | None
    name: str
    status: ActivityStatus
    start_event_id: str
    end_event_id: str | None
    start_time: datetime
    end_time: datetime | None
    duration_ms: int | None
    start_text: str
    end_text: str | None
    pairing_score: float


@dataclass
class TimeQueryResultDTO:
    """Data transfer object for time query results."""

    success: bool
    duration_ms: int | None
    events_found: list[EventDTO]
    activities_found: list[ActivityDTO]
    response_text: str


# ---------------------------------------------------------------------------
# Storage Interfaces
# ---------------------------------------------------------------------------


class InteractionRepository(ABC):
    """Repository interface for interaction storage operations."""

    @abstractmethod
    def save(self, interaction: InteractionDTO) -> str:
        """Save an interaction and return its ID.

        Args:
            interaction: The interaction to save.

        Returns:
            The generated document ID.
        """
        ...

    @abstractmethod
    def get_by_id(self, interaction_id: str) -> InteractionDTO | None:
        """Retrieve an interaction by ID.

        Args:
            interaction_id: The interaction ID.

        Returns:
            The interaction or None if not found.
        """
        ...

    @abstractmethod
    def get_by_date_range(
        self, start: datetime, end: datetime, limit: int = 100
    ) -> list[InteractionDTO]:
        """Get interactions within a date range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            limit: Maximum number to return.

        Returns:
            List of interactions, most recent first.
        """
        ...

    @abstractmethod
    def get_recent(self, limit: int = 10) -> list[InteractionDTO]:
        """Get recent interactions.

        Args:
            limit: Maximum number to return.

        Returns:
            List of interactions, most recent first.
        """
        ...

    @abstractmethod
    def search_transcript(self, query: str, limit: int = 20) -> list[InteractionDTO]:
        """Search interactions by transcript text.

        Args:
            query: Search query string.
            limit: Maximum number to return.

        Returns:
            List of matching interactions.
        """
        ...


class EventRepository(ABC):
    """Repository interface for event storage operations."""

    @abstractmethod
    def save(self, event: EventDTO) -> str:
        """Save an event and return its ID.

        Args:
            event: The event to save.

        Returns:
            The generated document ID.
        """
        ...

    @abstractmethod
    def get_by_id(self, event_id: str) -> EventDTO | None:
        """Retrieve an event by ID.

        Args:
            event_id: The event ID.

        Returns:
            The event or None if not found.
        """
        ...

    @abstractmethod
    def get_by_type(
        self, event_type: EventType, limit: int = 50
    ) -> list[EventDTO]:
        """Get events by type.

        Args:
            event_type: The event type to filter by.
            limit: Maximum number to return.

        Returns:
            List of events, most recent first.
        """
        ...

    @abstractmethod
    def get_around_time(
        self, time_point: datetime, window_minutes: int = 15
    ) -> list[EventDTO]:
        """Get events around a specific time point.

        FR-003: Search for activities within a specified time window.

        Args:
            time_point: The center time point.
            window_minutes: Minutes before and after to include.

        Returns:
            List of events within the time window.
        """
        ...

    @abstractmethod
    def get_in_range(self, start: datetime, end: datetime) -> list[EventDTO]:
        """Get events within a time range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            List of events in the range.
        """
        ...

    @abstractmethod
    def find_unlinked_start_events(
        self, context: str, max_age_hours: int = 4
    ) -> list[EventDTO]:
        """Find unlinked activity_start events for pairing.

        Used for semantic similarity matching to link end events.

        Args:
            context: The context/activity description to match.
            max_age_hours: Maximum hours ago to search.

        Returns:
            List of candidate start events.
        """
        ...

    @abstractmethod
    def link_events(self, start_id: str, end_id: str) -> None:
        """Link two events as a start/end pair.

        Args:
            start_id: The start event ID.
            end_id: The end event ID.
        """
        ...


class ActivityRepository(ABC):
    """Repository interface for activity storage operations."""

    @abstractmethod
    def save(self, activity: ActivityDTO) -> str:
        """Save an activity and return its ID.

        Args:
            activity: The activity to save.

        Returns:
            The generated document ID.
        """
        ...

    @abstractmethod
    def get_by_id(self, activity_id: str) -> ActivityDTO | None:
        """Retrieve an activity by ID.

        Args:
            activity_id: The activity ID.

        Returns:
            The activity or None if not found.
        """
        ...

    @abstractmethod
    def get_in_progress(self) -> list[ActivityDTO]:
        """Get all in-progress activities.

        Returns:
            List of activities with status IN_PROGRESS.
        """
        ...

    @abstractmethod
    def complete(
        self, activity_id: str, end_event_id: str, end_time: datetime
    ) -> ActivityDTO:
        """Mark an activity as completed.

        Args:
            activity_id: The activity ID.
            end_event_id: The end event ID.
            end_time: The end timestamp.

        Returns:
            The updated activity with duration calculated.
        """
        ...

    @abstractmethod
    def get_by_name(self, name: str, limit: int = 10) -> list[ActivityDTO]:
        """Get activities by name.

        Args:
            name: Activity name to search.
            limit: Maximum number to return.

        Returns:
            List of matching activities, most recent first.
        """
        ...

    @abstractmethod
    def calculate_average_duration(self, name: str) -> int | None:
        """Calculate average duration for an activity type.

        Args:
            name: Activity name.

        Returns:
            Average duration in milliseconds, or None if no data.
        """
        ...


# ---------------------------------------------------------------------------
# Service Interfaces
# ---------------------------------------------------------------------------


class EventExtractor(ABC):
    """Interface for extracting events from natural language."""

    @abstractmethod
    def extract(self, transcript: str, timestamp: datetime) -> list[EventDTO]:
        """Extract events from a transcript.

        FR-004: Extract meaningful events from natural language input.

        Args:
            transcript: The user's spoken text.
            timestamp: When the interaction occurred.

        Returns:
            List of extracted events (may be empty).
        """
        ...


class EventPairer(ABC):
    """Interface for pairing related events."""

    @abstractmethod
    def find_matching_start(self, end_event: EventDTO) -> tuple[EventDTO, float] | None:
        """Find a matching start event for an end event.

        Uses semantic similarity + time proximity (per spec clarifications).

        Args:
            end_event: The end event to match.

        Returns:
            Tuple of (matching start event, pairing score) or None.
        """
        ...

    @abstractmethod
    def calculate_similarity(self, context1: str, context2: str) -> float:
        """Calculate semantic similarity between two contexts.

        Args:
            context1: First context string.
            context2: Second context string.

        Returns:
            Similarity score 0-1.
        """
        ...


class TimeQueryHandler(ABC):
    """Interface for handling time-based queries."""

    @abstractmethod
    def query_duration(self, event1_desc: str, event2_desc: str) -> TimeQueryResultDTO:
        """Query the duration between two events.

        FR-002: Support querying time duration between two events.
        FR-009: Return human-friendly time durations.

        Args:
            event1_desc: Description of the first event.
            event2_desc: Description of the second event.

        Returns:
            Query result with duration and human-readable response.
        """
        ...

    @abstractmethod
    def query_around_time(
        self, time_point: datetime, window_minutes: int = 15
    ) -> TimeQueryResultDTO:
        """Query events around a specific time.

        FR-003: Search for activities within a specified time window.

        Args:
            time_point: The time to search around.
            window_minutes: Minutes before and after to include.

        Returns:
            Query result with events found.
        """
        ...

    @abstractmethod
    def query_range(self, start: datetime, end: datetime) -> TimeQueryResultDTO:
        """Query events within a time range.

        Args:
            start: Start of range.
            end: End of range.

        Returns:
            Query result with events found.
        """
        ...

    @abstractmethod
    def format_duration(self, milliseconds: int) -> str:
        """Format a duration in milliseconds to human-readable text.

        FR-009: Return human-friendly time durations.

        Args:
            milliseconds: Duration in milliseconds.

        Returns:
            Human-friendly string (e.g., "about 2 hours and 15 minutes").
        """
        ...


# ---------------------------------------------------------------------------
# Storage Client Interface
# ---------------------------------------------------------------------------


class StorageClient(ABC):
    """High-level interface for the MongoDB storage system."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to MongoDB.

        FR-006: Provide fallback behavior when unavailable.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to MongoDB.

        Returns:
            True if connected, False otherwise.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Perform a health check on the database.

        Returns:
            True if healthy, False otherwise.
        """
        ...

    @property
    @abstractmethod
    def interactions(self) -> InteractionRepository:
        """Get the interactions repository."""
        ...

    @property
    @abstractmethod
    def events(self) -> EventRepository:
        """Get the events repository."""
        ...

    @property
    @abstractmethod
    def activities(self) -> ActivityRepository:
        """Get the activities repository."""
        ...
