"""Time query command handler for voice assistant.

Handles duration queries, around-time searches, and event logging.
"""

import logging
import re
from datetime import UTC, datetime
from typing import Protocol

from ..storage.events import ActivityRepository, EventRepository
from ..storage.models import ActivityDTO, ActivityStatus, EventDTO, EventType
from ..storage.queries import TimeQueryHandler

logger = logging.getLogger(__name__)


class StorageAccess(Protocol):
    """Protocol for storage access in time queries."""

    @property
    def events(self) -> EventRepository: ...

    @property
    def activities(self) -> ActivityRepository: ...


class TimeQueryCommandHandler:
    """Handles time-based voice commands.

    Wraps TimeQueryHandler for orchestrator integration.
    """

    def __init__(self, storage: StorageAccess | None = None) -> None:
        """Initialize command handler.

        Args:
            storage: Storage access for queries. If None, commands will fail gracefully.
        """
        self._storage = storage
        self._query_handler: TimeQueryHandler | None = None
        if storage is not None:
            self._query_handler = TimeQueryHandler(storage)

    def handle_duration_query(self, activity_description: str) -> str:
        """Handle 'how long was I...' queries.

        Args:
            activity_description: Activity to query (e.g., 'shower', 'gym')

        Returns:
            Human-readable response.
        """
        if self._query_handler is None:
            return "I can't answer time queries right now. Storage is not available."

        result = self._query_handler.query_duration(activity_description)
        return result.response_text

    def handle_activity_search(
        self,
        time_ref: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> str:
        """Handle 'what was I doing around...' queries.

        Args:
            time_ref: Point time reference (e.g., '10 AM', 'noon')
            start_time: Start of range (for range queries)
            end_time: End of range (for range queries)

        Returns:
            Human-readable response.
        """
        if self._query_handler is None:
            return "I can't answer time queries right now. Storage is not available."

        if start_time and end_time:
            # Range query
            parsed_start = self._parse_time_reference(start_time)
            parsed_end = self._parse_time_reference(end_time)

            if parsed_start is None or parsed_end is None:
                return f"I couldn't understand the time range '{start_time}' to '{end_time}'."

            result = self._query_handler.query_range(parsed_start, parsed_end)
            return result.response_text

        elif time_ref:
            # Point query
            parsed_time = self._parse_time_reference(time_ref)

            if parsed_time is None:
                return f"I couldn't understand the time '{time_ref}'."

            result = self._query_handler.query_around_time(parsed_time)
            return result.response_text

        return "I need a time reference to search. Try 'what was I doing around 10 AM?'"

    def handle_event_log(
        self,
        context: str,
        event_type: str,
        interaction_id: str,
    ) -> str:
        """Handle event logging ('I'm going to the gym').

        Args:
            context: Event context/description (e.g., 'gym')
            event_type: Type of event ('activity_start', 'activity_end', 'note')
            interaction_id: ID of the triggering interaction

        Returns:
            Human-readable confirmation.
        """
        if self._storage is None:
            return "I can't log events right now. Storage is not available."

        # Map string to EventType
        type_map = {
            "activity_start": EventType.ACTIVITY_START,
            "activity_end": EventType.ACTIVITY_END,
            "note": EventType.NOTE,
        }

        evt_type = type_map.get(event_type, EventType.NOTE)

        # Create and save event
        event = EventDTO(
            interaction_id=interaction_id,
            timestamp=datetime.now(UTC),
            event_type=evt_type,
            context=context,
            source_text=context,
            extraction_confidence=1.0,  # User explicitly stated
        )

        event_id = self._storage.events.save(event)
        logger.info(f"Logged event {event_id}: {evt_type.value} - {context}")

        # Generate response based on event type
        if evt_type == EventType.ACTIVITY_START:
            # Create in-progress activity
            activity = ActivityDTO(
                name=context,
                status=ActivityStatus.IN_PROGRESS,
                start_event_id=event_id,
                start_time=datetime.now(UTC),
                start_text=context,
                pairing_score=1.0,
            )
            self._storage.activities.save(activity)
            return f"Got it, I'll track your {context}."

        elif evt_type == EventType.ACTIVITY_END:
            # Try to complete matching in-progress activity
            in_progress = self._storage.activities.get_in_progress()
            for activity in in_progress:
                if self._contexts_match(activity.name, context):
                    completed = self._storage.activities.complete(
                        activity_id=activity.id,  # type: ignore
                        end_event_id=event_id,
                        end_time=datetime.now(UTC),
                        end_text=context,
                    )
                    if completed and completed.duration_ms:
                        duration_str = self._query_handler.format_duration(  # type: ignore
                            completed.duration_ms
                        )
                        return f"Got it. Your {activity.name} took {duration_str}."
                    return f"Got it. I've marked your {activity.name} as complete."

            return f"Noted that you finished {context}."

        else:  # NOTE
            return f"Got it, I've noted: {context}."

    def _parse_time_reference(self, time_str: str) -> datetime | None:
        """Parse natural language time reference to datetime.

        Args:
            time_str: Time reference like '10 AM', 'noon', '3:30 PM'

        Returns:
            datetime for today at that time, or None if can't parse.
        """
        time_str = time_str.strip().lower()
        today = datetime.now(UTC).date()

        # Handle special words
        if time_str in ("noon", "12 noon"):
            return datetime.combine(today, datetime.min.time().replace(hour=12), tzinfo=UTC)
        elif time_str == "midnight":
            return datetime.combine(today, datetime.min.time(), tzinfo=UTC)

        # Try parsing standard time formats
        formats = [
            "%I %p",  # "10 AM"
            "%I:%M %p",  # "10:30 AM"
            "%I%p",  # "10am"
            "%I:%M%p",  # "10:30am"
            "%H:%M",  # "14:30"
        ]

        for fmt in formats:
            try:
                parsed = datetime.strptime(time_str, fmt)
                return datetime.combine(today, parsed.time(), tzinfo=UTC)
            except ValueError:
                continue

        # Try extracting numbers (e.g., "around 10" -> 10:00)
        match = re.search(r"\b(\d{1,2})\b", time_str)
        if match:
            hour = int(match.group(1))
            if 1 <= hour <= 12:
                # Assume AM/PM based on current time
                now = datetime.now(UTC)
                if now.hour < 12:
                    return datetime.combine(
                        today, datetime.min.time().replace(hour=hour), tzinfo=UTC
                    )
                else:
                    return datetime.combine(
                        today,
                        datetime.min.time().replace(hour=hour + 12 if hour < 12 else hour),
                        tzinfo=UTC,
                    )

        return None

    def handle_yesterday_query(self) -> str:
        """Handle 'what did I do yesterday?' queries.

        Returns:
            Human-readable summary of yesterday's activities.
        """
        if self._query_handler is None:
            return "I can't answer historical queries right now. Storage is not available."

        result = self._query_handler.query_yesterday()
        return result.response_text

    def handle_last_mention(self, topic: str) -> str:
        """Handle 'when did I last mention...' queries.

        Args:
            topic: Topic to search for.

        Returns:
            Human-readable response about last mention.
        """
        if self._query_handler is None:
            return "I can't answer historical queries right now. Storage is not available."

        result = self._query_handler.query_last_mention(topic)
        return result.response_text

    def _contexts_match(self, context1: str, context2: str) -> bool:
        """Check if two contexts refer to the same activity.

        Args:
            context1: First context string.
            context2: Second context string.

        Returns:
            True if contexts likely match.
        """
        # Normalize strings
        c1 = context1.lower().strip()
        c2 = context2.lower().strip()

        # Direct match
        if c1 == c2:
            return True

        # One contains the other
        if c1 in c2 or c2 in c1:
            return True

        # Check for common activity keywords
        keywords = ["shower", "gym", "workout", "lunch", "dinner", "breakfast", "meeting", "walk"]
        return any(kw in c1 and kw in c2 for kw in keywords)


__all__ = ["TimeQueryCommandHandler"]
