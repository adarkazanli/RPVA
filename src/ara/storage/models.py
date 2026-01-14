"""Data models for MongoDB storage.

Defines DTOs and enums for interactions, events, and activities.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
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

    DURATION = "duration"
    RANGE_SEARCH = "range_search"
    POINT_SEARCH = "point_search"


@dataclass
class InteractionDTO:
    """Data transfer object for voice interactions."""

    session_id: str
    timestamp: datetime
    device_id: str
    transcript: str
    transcript_confidence: float
    intent_type: str
    intent_confidence: float
    response_text: str
    response_source: str
    latency_ms: dict[str, int]
    id: str | None = None
    entities: dict[str, Any] = field(default_factory=dict)
    events_extracted: list[str] = field(default_factory=list)
    audio_duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "input": {
                "transcript": self.transcript,
                "confidence": self.transcript_confidence,
                "audio_duration_ms": self.audio_duration_ms,
            },
            "intent": {
                "type": self.intent_type,
                "confidence": self.intent_confidence,
                "entities": self.entities,
            },
            "response": {
                "text": self.response_text,
                "source": self.response_source,
            },
            "latency_ms": self.latency_ms,
            "events_extracted": self.events_extracted,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InteractionDTO":
        """Create from MongoDB document."""
        return cls(
            id=str(data.get("_id", "")),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", datetime.now()),
            device_id=data.get("device_id", ""),
            transcript=data.get("input", {}).get("transcript", ""),
            transcript_confidence=data.get("input", {}).get("confidence", 0.0),
            audio_duration_ms=data.get("input", {}).get("audio_duration_ms", 0),
            intent_type=data.get("intent", {}).get("type", ""),
            intent_confidence=data.get("intent", {}).get("confidence", 0.0),
            entities=data.get("intent", {}).get("entities", {}),
            response_text=data.get("response", {}).get("text", ""),
            response_source=data.get("response", {}).get("source", ""),
            latency_ms=data.get("latency_ms", {}),
            events_extracted=data.get("events_extracted", []),
        )


@dataclass
class EventDTO:
    """Data transfer object for extracted events."""

    interaction_id: str
    timestamp: datetime
    event_type: EventType
    context: str
    source_text: str
    extraction_confidence: float
    id: str | None = None
    entities: dict[str, Any] = field(default_factory=dict)
    linked_event_id: str | None = None
    activity_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "interaction_id": self.interaction_id,
            "timestamp": self.timestamp,
            "type": self.event_type.value,
            "context": self.context,
            "entities": self.entities,
            "linked_event_id": self.linked_event_id,
            "activity_id": self.activity_id,
            "metadata": {
                "source_text": self.source_text,
                "extraction_confidence": self.extraction_confidence,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EventDTO":
        """Create from MongoDB document."""
        return cls(
            id=str(data.get("_id", "")),
            interaction_id=str(data.get("interaction_id", "")),
            timestamp=data.get("timestamp", datetime.now()),
            event_type=EventType(data.get("type", "note")),
            context=data.get("context", ""),
            entities=data.get("entities", {}),
            linked_event_id=data.get("linked_event_id"),
            activity_id=data.get("activity_id"),
            source_text=data.get("metadata", {}).get("source_text", ""),
            extraction_confidence=data.get("metadata", {}).get("extraction_confidence", 0.0),
        )


@dataclass
class ActivityDTO:
    """Data transfer object for paired activities."""

    name: str
    status: ActivityStatus
    start_event_id: str
    start_time: datetime
    start_text: str
    pairing_score: float
    id: str | None = None
    end_event_id: str | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None
    end_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for MongoDB storage."""
        return {
            "name": self.name,
            "status": self.status.value,
            "start_event_id": self.start_event_id,
            "end_event_id": self.end_event_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "context": {
                "start_text": self.start_text,
                "end_text": self.end_text,
            },
            "pairing_score": self.pairing_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ActivityDTO":
        """Create from MongoDB document."""
        start_time = data.get("start_time", datetime.now(UTC))
        end_time = data.get("end_time")
        # Ensure timezone awareness (MongoDB may return naive datetimes)
        if start_time and start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        if end_time and end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=UTC)
        return cls(
            id=str(data.get("_id", "")),
            name=data.get("name", ""),
            status=ActivityStatus(data.get("status", "in_progress")),
            start_event_id=str(data.get("start_event_id", "")),
            end_event_id=data.get("end_event_id"),
            start_time=start_time,
            end_time=end_time,
            duration_ms=data.get("duration_ms"),
            start_text=data.get("context", {}).get("start_text", ""),
            end_text=data.get("context", {}).get("end_text"),
            pairing_score=data.get("pairing_score", 0.0),
        )


@dataclass
class TimeQueryResultDTO:
    """Data transfer object for time query results."""

    success: bool
    response_text: str
    duration_ms: int | None = None
    events_found: list[EventDTO] = field(default_factory=list)
    activities_found: list[ActivityDTO] = field(default_factory=list)


__all__ = [
    "EventType",
    "ActivityStatus",
    "TimeQueryType",
    "InteractionDTO",
    "EventDTO",
    "ActivityDTO",
    "TimeQueryResultDTO",
]
