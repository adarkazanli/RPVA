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
    TimeQueryResultDTO,
    TimeQueryType,
)
from .queries import TimeQueryHandler

__all__ = [
    "MongoStorageClient",
    "InteractionDTO",
    "EventDTO",
    "ActivityDTO",
    "TimeQueryResultDTO",
    "EventType",
    "ActivityStatus",
    "TimeQueryType",
    "TimeQueryHandler",
    "EventRepository",
    "ActivityRepository",
    "EventExtractor",
    "EventPairer",
]
