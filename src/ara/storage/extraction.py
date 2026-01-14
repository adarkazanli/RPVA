"""Event extraction and pairing for natural language processing.

Extracts events from user speech and pairs activity start/end events.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

from .events import ActivityRepository, EventRepository
from .models import ActivityDTO, ActivityStatus, EventDTO, EventType


class EventExtractor:
    """Extracts events from natural language transcripts.

    Identifies activity starts, activity ends, and notes from user speech.
    """

    # Activity start patterns
    START_PATTERNS = [
        (r"(?:i'?m|i\s+am)\s+(?:going\s+)?(?:to\s+)?(?:take|have)\s+(?:a\s+)?(\w+)", 0.95),
        (r"(?:i'?m|i\s+am)\s+(?:going|heading|off)\s+to\s+(?:the\s+)?(\w+)", 1.0),
        (r"(?:i'?m|i\s+am)\s+(?:starting|beginning)\s+(?:my\s+)?(\w+)", 0.95),
        (r"(?:i'?m|i\s+am)\s+about\s+to\s+(?:start\s+)?(\w+)", 0.9),
        (r"(?:starting|beginning)\s+(?:my\s+)?(\w+)", 0.85),
    ]

    # Activity end patterns
    END_PATTERNS = [
        (r"(?:i'?m|i\s+am)\s+back\s+from\s+(?:the\s+)?(\w+)", 0.95),
        (r"(?:i'?m|i\s+am)\s+(?:done|finished)\s+(?:with\s+)?(?:my\s+)?(?:the\s+)?(\w+)?", 0.95),
        (r"(?:just\s+)?finished\s+(?:my\s+)?(?:the\s+)?(\w+)", 0.95),
        (r"(?:just\s+)?(?:got\s+)?(?:done|completed)\s+(?:with\s+)?(?:my\s+)?(?:the\s+)?(\w+)", 0.95),
        (r"(?:i'?m|i\s+am)\s+(?:leaving|left)\s+(?:the\s+)?(\w+)", 0.9),
        (r"(?:ended|stopped)\s+(?:my\s+)?(\w+)", 0.85),
    ]

    # Note patterns
    NOTE_PATTERNS = [
        (r"(?:remember|note|memo)[,:\s]+(.+)", 0.95),
        (r"(?:make\s+a\s+)?note[:\s]+(.+)", 0.95),
        (r"(?:i\s+)?parked\s+(?:at|in|on)\s+(.+)", 0.9),
    ]

    def __init__(self) -> None:
        """Initialize the extractor with compiled patterns."""
        self._start_patterns = [
            (re.compile(p, re.IGNORECASE), conf) for p, conf in self.START_PATTERNS
        ]
        self._end_patterns = [
            (re.compile(p, re.IGNORECASE), conf) for p, conf in self.END_PATTERNS
        ]
        self._note_patterns = [
            (re.compile(p, re.IGNORECASE), conf) for p, conf in self.NOTE_PATTERNS
        ]

    def extract(self, transcript: str, interaction_id: str) -> list[EventDTO]:
        """Extract events from a transcript.

        Args:
            transcript: User's spoken text.
            interaction_id: ID of the source interaction.

        Returns:
            List of extracted EventDTO objects.
        """
        events: list[EventDTO] = []
        timestamp = datetime.now(UTC)

        # Try activity start patterns
        for pattern, confidence in self._start_patterns:
            match = pattern.search(transcript)
            if match:
                context = match.group(1) if match.groups() else ""
                if context:
                    events.append(
                        EventDTO(
                            interaction_id=interaction_id,
                            timestamp=timestamp,
                            event_type=EventType.ACTIVITY_START,
                            context=context.strip(),
                            source_text=transcript,
                            extraction_confidence=confidence,
                        )
                    )
                    break

        # Try activity end patterns
        for pattern, confidence in self._end_patterns:
            match = pattern.search(transcript)
            if match:
                context = match.group(1) if match.groups() and match.group(1) else "activity"
                events.append(
                    EventDTO(
                        interaction_id=interaction_id,
                        timestamp=timestamp,
                        event_type=EventType.ACTIVITY_END,
                        context=context.strip(),
                        source_text=transcript,
                        extraction_confidence=confidence,
                    )
                )
                break

        # Try note patterns
        for pattern, confidence in self._note_patterns:
            match = pattern.search(transcript)
            if match:
                context = match.group(1) if match.groups() else ""
                if context:
                    events.append(
                        EventDTO(
                            interaction_id=interaction_id,
                            timestamp=timestamp,
                            event_type=EventType.NOTE,
                            context=context.strip(),
                            source_text=transcript,
                            extraction_confidence=confidence,
                        )
                    )
                    break

        return events


class EventPairer:
    """Pairs activity start and end events.

    Uses semantic similarity and temporal proximity to match events.
    """

    # Default synonyms for common activities
    DEFAULT_SYNONYMS: dict[str, set[str]] = {
        "gym": {"workout", "training", "exercise", "fitness", "weights"},
        "shower": {"bath", "washing", "rinse"},
        "cooking": {"making food", "preparing", "meal prep", "kitchen"},
        "workout": {"gym", "exercise", "training", "fitness"},
        "lunch": {"eating", "meal", "food"},
        "dinner": {"eating", "meal", "food", "supper"},
        "breakfast": {"eating", "meal", "food", "morning"},
        "meeting": {"call", "conference", "discussion"},
        "work": {"office", "job", "working"},
        "walk": {"walking", "stroll", "hike"},
        "run": {"running", "jogging", "jog"},
    }

    def __init__(
        self,
        event_repo: EventRepository,
        activity_repo: ActivityRepository,
        synonyms_path: Path | None = None,
    ) -> None:
        """Initialize the pairer.

        Args:
            event_repo: Repository for events.
            activity_repo: Repository for activities.
            synonyms_path: Optional path to custom synonyms JSON file.
        """
        self._event_repo = event_repo
        self._activity_repo = activity_repo
        self._synonyms = self._load_synonyms(synonyms_path)

    def _load_synonyms(self, path: Path | None) -> dict[str, set[str]]:
        """Load synonyms from file or use defaults."""
        if path and path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    return {k: set(v) for k, v in data.items()}
            except Exception:
                pass
        return self.DEFAULT_SYNONYMS.copy()

    def calculate_similarity(self, context1: str, context2: str) -> float:
        """Calculate semantic similarity between two contexts.

        Args:
            context1: First context string.
            context2: Second context string.

        Returns:
            Similarity score between 0 and 1.
        """
        c1 = context1.lower().strip()
        c2 = context2.lower().strip()

        # Exact match
        if c1 == c2:
            return 1.0

        # One contains the other
        if c1 in c2 or c2 in c1:
            return 0.9

        # Check synonyms
        c1_words = set(c1.split())
        c2_words = set(c2.split())

        for word in c1_words:
            synonyms = self._synonyms.get(word, set())
            if word in c2_words or any(syn in c2 for syn in synonyms):
                return 0.8

        for word in c2_words:
            synonyms = self._synonyms.get(word, set())
            if word in c1_words or any(syn in c1 for syn in synonyms):
                return 0.8

        # Word overlap
        overlap = c1_words & c2_words
        if overlap:
            total_words = len(c1_words | c2_words)
            return 0.5 * len(overlap) / total_words

        return 0.0

    def find_matching_start(
        self,
        end_event: EventDTO,
        max_age_hours: int = 4,
        min_score: float = 0.7,
    ) -> EventDTO | None:
        """Find matching start event for an end event.

        Args:
            end_event: The activity end event to match.
            max_age_hours: Maximum hours back to search.
            min_score: Minimum similarity score required.

        Returns:
            Matching start event or None if no good match found.
        """
        # Get unlinked start events
        candidates = self._event_repo.find_unlinked_start_events(
            context=end_event.context,
            max_age_hours=max_age_hours,
        )

        if not candidates:
            return None

        best_match: EventDTO | None = None
        best_score = min_score

        for candidate in candidates:
            # Skip events after the end event (wrong temporal order)
            if candidate.timestamp >= end_event.timestamp:
                continue

            # Calculate composite score
            semantic_score = self.calculate_similarity(candidate.context, end_event.context)

            # Temporal score: prefer more recent starts
            time_diff = end_event.timestamp - candidate.timestamp
            hours_diff = time_diff.total_seconds() / 3600
            temporal_score = max(0, 1 - (hours_diff / max_age_hours))

            # Combined score
            score = 0.7 * semantic_score + 0.3 * temporal_score

            if score > best_score:
                best_score = score
                best_match = candidate

        return best_match

    def pair_event(self, end_event: EventDTO) -> ActivityDTO | None:
        """Attempt to pair an end event with a start event.

        If a match is found, creates and stores the activity.

        Args:
            end_event: The activity end event to pair.

        Returns:
            Created activity or None if no match found.
        """
        start_event = self.find_matching_start(end_event)
        if start_event is None:
            return None

        # Link the events
        if start_event.id and end_event.id:
            self._event_repo.link_events(start_event.id, end_event.id)

        # Calculate duration
        duration_ms = int(
            (end_event.timestamp - start_event.timestamp).total_seconds() * 1000
        )

        # Create activity
        activity = ActivityDTO(
            name=start_event.context,
            status=ActivityStatus.COMPLETED,
            start_event_id=start_event.id or "",
            end_event_id=end_event.id,
            start_time=start_event.timestamp,
            end_time=end_event.timestamp,
            duration_ms=duration_ms,
            start_text=start_event.source_text,
            end_text=end_event.source_text,
            pairing_score=self.calculate_similarity(start_event.context, end_event.context),
        )

        self._activity_repo.save(activity)
        return activity


__all__ = ["EventExtractor", "EventPairer"]
