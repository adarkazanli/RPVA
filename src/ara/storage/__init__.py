"""MongoDB storage module for Ara voice assistant.

Provides persistent storage for interactions, events, and activities
with support for time-based queries and event pairing.
"""

from .client import MongoStorageClient
from .events import ActivityRepository, EventRepository
from .extraction import EventExtractor, EventPairer
from .models import (
    ActivityDTO,
    ActivityStatus,
    EventDTO,
    EventType,
    InteractionDTO,
    NoteDTO,
    TimeQueryResultDTO,
    TimeQueryType,
    TimeTrackingActivityDTO,
)
from .notes import (
    MongoActivityDataSource,
    NoteRepository,
    TimeTrackingActivityRepository,
)
from .queries import TimeQueryHandler

__all__ = [
    "MongoStorageClient",
    "InteractionDTO",
    "EventDTO",
    "ActivityDTO",
    "NoteDTO",
    "TimeTrackingActivityDTO",
    "TimeQueryResultDTO",
    "EventType",
    "ActivityStatus",
    "TimeQueryType",
    "TimeQueryHandler",
    "EventRepository",
    "ActivityRepository",
    "NoteRepository",
    "TimeTrackingActivityRepository",
    "MongoActivityDataSource",
    "EventExtractor",
    "EventPairer",
]
