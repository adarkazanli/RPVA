"""Note service for capturing and querying notes.

Provides CRUD operations for notes with entity extraction.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Protocol

from .categorizer import categorize
from .extractor import EntityExtractor
from .models import Category, Note

logger = logging.getLogger(__name__)


class NoteRepository(Protocol):
    """Protocol for note persistence."""

    def insert(self, note: dict[str, Any]) -> str:
        """Insert note and return ID."""
        ...

    def find_by_person(self, person: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find notes mentioning a person."""
        ...

    def find_by_topic(self, topic: str, limit: int = 10) -> list[dict[str, Any]]:
        """Find notes about a topic."""
        ...

    def find_by_date_range(
        self, start: datetime, end: datetime, category: str | None = None
    ) -> list[dict[str, Any]]:
        """Find notes in date range."""
        ...


class NoteService:
    """Service for capturing and querying notes.

    Handles entity extraction, categorization, and persistence.
    """

    def __init__(
        self,
        extractor: EntityExtractor,
        repository: NoteRepository | None = None,
        user_id: str = "default",
    ) -> None:
        """Initialize note service.

        Args:
            extractor: Entity extractor for processing transcripts
            repository: Optional repository for persistence
            user_id: Default user ID for notes
        """
        self._extractor = extractor
        self._repository = repository
        self._user_id = user_id

    def capture(self, transcript: str, activity_id: str | None = None) -> Note:
        """Capture a new note with automatic entity extraction.

        Args:
            transcript: Raw voice transcript
            activity_id: Optional associated activity

        Returns:
            Note with extracted entities and assigned category
        """
        # Extract entities
        entities = self._extractor.extract(transcript)

        # Auto-categorize based on content
        category = categorize(transcript)

        # Create note
        note = Note(
            transcript=transcript,
            category=category,
            timestamp=datetime.now(UTC),
            people=entities.people,
            topics=entities.topics,
            locations=entities.locations,
            activity_id=activity_id,
            user_id=self._user_id,
        )

        # Persist if repository available
        if self._repository:
            note_id = self._repository.insert(note.to_dict())
            note.id = note_id

        logger.info(
            f"Captured note: people={entities.people}, "
            f"topics={entities.topics}, category={category.value}"
        )

        return note

    def find_by_person(self, person_name: str, limit: int = 10) -> list[Note]:
        """Find notes mentioning a specific person.

        Args:
            person_name: Name to search for (case-insensitive)
            limit: Maximum results to return

        Returns:
            List of matching notes, most recent first
        """
        if not self._repository:
            logger.warning("No repository configured for note queries")
            return []

        docs = self._repository.find_by_person(person_name, limit)
        return [Note.from_dict(doc) for doc in docs]

    def find_by_topic(self, topic: str, limit: int = 10) -> list[Note]:
        """Find notes about a specific topic.

        Args:
            topic: Topic to search for (case-insensitive)
            limit: Maximum results to return

        Returns:
            List of matching notes, most recent first
        """
        if not self._repository:
            logger.warning("No repository configured for note queries")
            return []

        docs = self._repository.find_by_topic(topic, limit)
        return [Note.from_dict(doc) for doc in docs]

    def find_by_date_range(
        self,
        start: datetime,
        end: datetime,
        category: Category | None = None,
    ) -> list[Note]:
        """Find notes within a date range.

        Args:
            start: Range start (inclusive)
            end: Range end (inclusive)
            category: Optional category filter

        Returns:
            List of matching notes, most recent first
        """
        if not self._repository:
            logger.warning("No repository configured for note queries")
            return []

        category_str = category.value if category else None
        docs = self._repository.find_by_date_range(start, end, category_str)
        return [Note.from_dict(doc) for doc in docs]


__all__ = ["NoteService", "NoteRepository"]
