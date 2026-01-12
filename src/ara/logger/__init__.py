"""Logger module for Ara Voice Assistant.

Provides interaction logging, storage, and daily summary generation.
"""

from ara.logger.interaction import (
    Interaction,
    InteractionLogger,
    OperationMode,
    ResponseSource,
    Session,
    SessionState,
)
from ara.logger.storage import (
    InteractionStorage,
    JSONLWriter,
    SQLiteStorage,
)
from ara.logger.summary import (
    ActionItem,
    DailySummary,
    SummaryGenerator,
    extract_action_items,
)

__all__ = [
    # Interaction
    "Interaction",
    "InteractionLogger",
    "OperationMode",
    "ResponseSource",
    "Session",
    "SessionState",
    # Storage
    "InteractionStorage",
    "JSONLWriter",
    "SQLiteStorage",
    # Summary
    "ActionItem",
    "DailySummary",
    "SummaryGenerator",
    "extract_action_items",
]
