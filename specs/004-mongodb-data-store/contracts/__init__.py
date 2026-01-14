"""Contract interfaces for MongoDB Data Store feature.

This package contains abstract interface definitions that serve as
contracts for the implementation. These are specifications, not
implementations.
"""

from .storage import (
    ActivityDTO,
    ActivityRepository,
    ActivityStatus,
    EventDTO,
    EventExtractor,
    EventPairer,
    EventRepository,
    EventType,
    InteractionDTO,
    InteractionRepository,
    StorageClient,
    TimeQueryHandler,
    TimeQueryResultDTO,
    TimeQueryType,
)

__all__ = [
    # Enums
    "EventType",
    "ActivityStatus",
    "TimeQueryType",
    # DTOs
    "InteractionDTO",
    "EventDTO",
    "ActivityDTO",
    "TimeQueryResultDTO",
    # Repository interfaces
    "InteractionRepository",
    "EventRepository",
    "ActivityRepository",
    # Service interfaces
    "EventExtractor",
    "EventPairer",
    "TimeQueryHandler",
    # Client interface
    "StorageClient",
]
