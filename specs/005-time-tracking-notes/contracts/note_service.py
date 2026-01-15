"""Note Service Contract.

Defines the interface for note capture and entity extraction.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass
class ExtractedEntities:
    """Entities extracted from a note transcript."""

    people: list[str]
    topics: list[str]
    locations: list[str]


@dataclass
class NoteResult:
    """Result of capturing a note."""

    id: str
    transcript: str
    people: list[str]
    topics: list[str]
    locations: list[str]
    category: str
    timestamp: datetime


class EntityExtractor(Protocol):
    """Interface for extracting entities from text."""

    def extract(self, transcript: str) -> ExtractedEntities:
        """Extract people, topics, and locations from transcript.

        Args:
            transcript: Raw voice transcript

        Returns:
            ExtractedEntities with parsed data

        Performance:
            Must complete in <2 seconds
        """
        ...


class NoteService(Protocol):
    """Interface for note capture and retrieval."""

    def capture(self, transcript: str, activity_id: str | None = None) -> NoteResult:
        """Capture a new note with automatic entity extraction.

        Args:
            transcript: Raw voice transcript
            activity_id: Optional associated activity

        Returns:
            NoteResult with extracted entities and assigned category

        Performance:
            Must complete in <3 seconds (extraction + storage)
        """
        ...

    def find_by_person(self, person_name: str, limit: int = 10) -> list[NoteResult]:
        """Find notes mentioning a specific person.

        Args:
            person_name: Name to search for (case-insensitive)
            limit: Maximum results to return

        Returns:
            List of matching notes, most recent first

        Performance:
            Must complete in <2 seconds
        """
        ...

    def find_by_topic(self, topic: str, limit: int = 10) -> list[NoteResult]:
        """Find notes about a specific topic.

        Args:
            topic: Topic to search for (case-insensitive)
            limit: Maximum results to return

        Returns:
            List of matching notes, most recent first

        Performance:
            Must complete in <2 seconds
        """
        ...

    def find_by_date_range(
        self,
        start: datetime,
        end: datetime,
        category: str | None = None,
    ) -> list[NoteResult]:
        """Find notes within a date range.

        Args:
            start: Range start (inclusive)
            end: Range end (inclusive)
            category: Optional category filter

        Returns:
            List of matching notes, most recent first
        """
        ...
