"""Time-based query handlers for voice assistant.

Provides duration calculation, around-time search, and range queries.
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol

from .events import ActivityRepository, EventRepository
from .models import ActivityStatus, TimeQueryResultDTO


class StorageFacade(Protocol):
    """Protocol for storage access."""

    @property
    def events(self) -> EventRepository: ...

    @property
    def activities(self) -> ActivityRepository: ...


class TimeQueryHandler:
    """Handles time-based queries for voice assistant.

    Supports:
    - Duration queries: "How long was I in the shower?"
    - Around-time queries: "What was I doing around 10 AM?"
    - Range queries: "What happened between 9 AM and noon?"
    """

    def __init__(self, storage: StorageFacade) -> None:
        """Initialize handler with storage access.

        Args:
            storage: Storage facade providing access to events and activities.
        """
        self._storage = storage

    def format_duration(self, duration_ms: int) -> str:
        """Format duration in milliseconds to human-friendly string.

        Args:
            duration_ms: Duration in milliseconds.

        Returns:
            Human-friendly duration string like "about 2 hours and 15 minutes".
        """
        if duration_ms <= 0:
            return "less than a second"

        # Convert to total seconds
        total_seconds = duration_ms // 1000

        # Calculate components
        days = total_seconds // (24 * 60 * 60)
        remaining = total_seconds % (24 * 60 * 60)
        hours = remaining // (60 * 60)
        remaining = remaining % (60 * 60)
        minutes = remaining // 60
        seconds = remaining % 60

        parts: list[str] = []

        if days > 0:
            parts.append(f"{days} day" if days == 1 else f"{days} days")

        if hours > 0:
            parts.append(f"{hours} hour" if hours == 1 else f"{hours} hours")

        if minutes > 0 and days == 0:  # Don't show minutes if showing days
            parts.append(f"{minutes} minute" if minutes == 1 else f"{minutes} minutes")

        if seconds > 0 and hours == 0 and days == 0:  # Only show seconds for short durations
            parts.append(f"{seconds} second" if seconds == 1 else f"{seconds} seconds")

        if not parts:
            return "less than a second"

        if len(parts) == 1:
            return f"about {parts[0]}"
        elif len(parts) == 2:
            return f"about {parts[0]} and {parts[1]}"
        else:
            return f"about {', '.join(parts[:-1])}, and {parts[-1]}"

    def calculate_duration(self, start: datetime, end: datetime) -> int:
        """Calculate duration between two timestamps.

        Args:
            start: Start timestamp.
            end: End timestamp.

        Returns:
            Duration in milliseconds.

        Raises:
            ValueError: If end is before start.
        """
        duration = end - start
        duration_ms = int(duration.total_seconds() * 1000)

        if duration_ms < 0:
            raise ValueError("Duration cannot be negative (end is before start)")

        return duration_ms

    def query_duration(self, activity_name: str) -> TimeQueryResultDTO:
        """Query the duration of a named activity.

        Finds the most recent activity matching the name and returns its duration.

        Args:
            activity_name: Name or description of the activity to query.

        Returns:
            TimeQueryResultDTO with success status and duration or error message.
        """
        # Search for matching activities
        activities = self._storage.activities.get_by_name(activity_name, limit=5)

        if not activities:
            return TimeQueryResultDTO(
                success=False,
                response_text=f"I couldn't find any activity matching '{activity_name}'. "
                "Try asking about something you've logged, like 'shower' or 'gym'.",
            )

        # Use most recent activity (list is sorted by start_time DESC)
        activity = activities[0]

        # Handle in-progress activities
        if activity.status == ActivityStatus.IN_PROGRESS:
            # Calculate elapsed time
            elapsed_ms = self.calculate_duration(activity.start_time, datetime.now(UTC))
            formatted = self.format_duration(elapsed_ms)

            return TimeQueryResultDTO(
                success=True,
                response_text=f"Your {activity.name} is still in progress. "
                f"You've been at it for {formatted} so far.",
                duration_ms=elapsed_ms,
                activities_found=[activity],
            )

        # Handle completed activities
        if activity.duration_ms is not None:
            formatted = self.format_duration(activity.duration_ms)
            return TimeQueryResultDTO(
                success=True,
                response_text=f"Your last {activity.name} took {formatted}.",
                duration_ms=activity.duration_ms,
                activities_found=[activity],
            )

        # Activity completed but no duration recorded
        return TimeQueryResultDTO(
            success=False,
            response_text=f"I found your {activity.name} activity, but I don't have "
            "the end time recorded to calculate the duration.",
        )

    def query_around_time(
        self,
        time_point: datetime,
        window_minutes: int = 15,
    ) -> TimeQueryResultDTO:
        """Query events around a specific time point.

        Args:
            time_point: The center time point to search around.
            window_minutes: Minutes before and after to include (default 15).

        Returns:
            TimeQueryResultDTO with events found in the time window.
        """
        events = self._storage.events.get_around_time(time_point, window_minutes)

        if not events:
            time_str = time_point.strftime("%I:%M %p")
            return TimeQueryResultDTO(
                success=True,
                response_text=f"I don't have anything recorded around {time_str}.",
                events_found=[],
            )

        # Format response
        time_str = time_point.strftime("%I:%M %p")
        event_descriptions = [f"- {e.context} ({e.timestamp.strftime('%I:%M %p')})" for e in events]
        event_list = "\n".join(event_descriptions)

        return TimeQueryResultDTO(
            success=True,
            response_text=f"Around {time_str}, I found:\n{event_list}",
            events_found=events,
        )

    def query_range(self, start: datetime, end: datetime) -> TimeQueryResultDTO:
        """Query events within a time range.

        Args:
            start: Start of the range (inclusive).
            end: End of the range (inclusive).

        Returns:
            TimeQueryResultDTO with events found in the range.

        Raises:
            ValueError: If start is after end.
        """
        if start > end:
            raise ValueError("Start time must be before end time")

        events = self._storage.events.get_in_range(start, end)

        if not events:
            start_str = start.strftime("%I:%M %p")
            end_str = end.strftime("%I:%M %p")
            return TimeQueryResultDTO(
                success=True,
                response_text=f"Nothing recorded between {start_str} and {end_str}.",
                events_found=[],
            )

        # Format response
        start_str = start.strftime("%I:%M %p")
        end_str = end.strftime("%I:%M %p")
        event_descriptions = [f"- {e.context} ({e.timestamp.strftime('%I:%M %p')})" for e in events]
        event_list = "\n".join(event_descriptions)

        return TimeQueryResultDTO(
            success=True,
            response_text=f"Between {start_str} and {end_str}:\n{event_list}",
            events_found=events,
        )

    def query_yesterday(self) -> TimeQueryResultDTO:
        """Query activities from yesterday.

        Returns:
            TimeQueryResultDTO summarizing yesterday's activities.
        """
        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)

        # Get yesterday's date range
        start = datetime.combine(yesterday, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(yesterday, datetime.max.time(), tzinfo=UTC)

        events = self._storage.events.get_in_range(start, end)
        activities = self._storage.activities.get_completed_in_range(start, end)

        if not events and not activities:
            return TimeQueryResultDTO(
                success=True,
                response_text="I don't have any activities recorded for yesterday.",
                events_found=[],
                activities_found=[],
            )

        # Build summary
        summary_parts: list[str] = []

        if activities:
            summary_parts.append(f"Yesterday you had {len(activities)} recorded activities:")
            for activity in activities:
                if activity.duration_ms:
                    duration_str = self.format_duration(activity.duration_ms)
                    summary_parts.append(f"- {activity.name} ({duration_str})")
                else:
                    summary_parts.append(f"- {activity.name}")

        if events and not activities:
            summary_parts.append(f"Yesterday I noted {len(events)} events:")
            for event in events[:5]:  # Limit to 5
                time_str = event.timestamp.strftime("%I:%M %p")
                summary_parts.append(f"- {event.context} at {time_str}")
            if len(events) > 5:
                summary_parts.append(f"...and {len(events) - 5} more")

        return TimeQueryResultDTO(
            success=True,
            response_text="\n".join(summary_parts),
            events_found=events,
            activities_found=activities,
        )

    def query_last_mention(self, topic: str) -> TimeQueryResultDTO:
        """Find when a topic was last mentioned.

        Args:
            topic: The topic to search for.

        Returns:
            TimeQueryResultDTO with the last mention information.
        """
        # Search for events matching the topic
        events = self._storage.events.get_recent(limit=100)

        # Find events mentioning the topic
        topic_lower = topic.lower()
        matching_events = [
            e
            for e in events
            if topic_lower in e.context.lower() or topic_lower in e.source_text.lower()
        ]

        if not matching_events:
            return TimeQueryResultDTO(
                success=True,
                response_text=f"I don't have any record of you mentioning '{topic}'.",
                events_found=[],
            )

        # Get the most recent match
        most_recent = matching_events[0]  # Already sorted by timestamp DESC

        # Calculate time ago
        now = datetime.now(UTC)
        time_diff = now - most_recent.timestamp
        time_ago = self._format_time_ago(time_diff)

        return TimeQueryResultDTO(
            success=True,
            response_text=f"You last mentioned '{topic}' {time_ago}, "
            f"when you said: \"{most_recent.source_text}\"",
            events_found=[most_recent],
        )

    def _format_time_ago(self, diff: timedelta) -> str:
        """Format a time difference as human-readable 'ago' string.

        Args:
            diff: Time difference.

        Returns:
            Human-friendly string like "2 hours ago" or "yesterday".
        """
        total_seconds = int(diff.total_seconds())
        minutes = total_seconds // 60
        hours = minutes // 60
        days = hours // 24

        if days > 1:
            return f"{days} days ago"
        elif days == 1:
            return "yesterday"
        elif hours > 1:
            return f"{hours} hours ago"
        elif hours == 1:
            return "about an hour ago"
        elif minutes > 1:
            return f"{minutes} minutes ago"
        elif minutes == 1:
            return "a minute ago"
        else:
            return "just now"


__all__ = ["TimeQueryHandler"]
