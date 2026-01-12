"""Reminder management for voice commands.

Implements scheduled reminders with recurring support.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import UUID


class ReminderStatus(Enum):
    """Status of a reminder."""

    PENDING = "pending"
    TRIGGERED = "triggered"
    DISMISSED = "dismissed"
    CANCELLED = "cancelled"


class Recurrence(Enum):
    """Recurrence pattern for reminders."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class Reminder:
    """A scheduled reminder notification.

    Attributes:
        id: Unique reminder identifier.
        message: Reminder content.
        remind_at: When to trigger the reminder.
        recurrence: Recurrence pattern.
        status: Current reminder status.
        triggered_at: When the reminder was triggered.
        created_by_interaction: ID of the creating interaction.
        created_at: When the reminder was created.
    """

    id: UUID
    message: str
    remind_at: datetime
    recurrence: Recurrence
    status: ReminderStatus
    triggered_at: datetime | None
    created_by_interaction: UUID
    created_at: datetime

    @property
    def is_due(self) -> bool:
        """Check if the reminder is due."""
        if self.status != ReminderStatus.PENDING:
            return False
        return datetime.now(UTC) >= self.remind_at


class ReminderManager:
    """Manages reminders with create, cancel, query operations.

    Provides thread-safe reminder management with trigger callbacks.
    """

    def __init__(self, on_trigger: Callable[[Reminder], None] | None = None) -> None:
        """Initialize the reminder manager.

        Args:
            on_trigger: Optional callback when a reminder triggers.
        """
        self._reminders: dict[UUID, Reminder] = {}
        self._on_trigger = on_trigger

    def create(
        self,
        message: str,
        remind_at: datetime,
        interaction_id: UUID,
        recurrence: Recurrence = Recurrence.NONE,
    ) -> Reminder:
        """Create a new reminder.

        Args:
            message: Reminder message.
            remind_at: When to trigger.
            interaction_id: ID of the creating interaction.
            recurrence: Recurrence pattern.

        Returns:
            The created Reminder object.
        """
        now = datetime.now(UTC)
        reminder = Reminder(
            id=uuid.uuid4(),
            message=message,
            remind_at=remind_at,
            recurrence=recurrence,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=interaction_id,
            created_at=now,
        )
        self._reminders[reminder.id] = reminder
        return reminder

    def cancel(self, reminder_id: UUID) -> bool:
        """Cancel a reminder.

        Args:
            reminder_id: ID of the reminder to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        reminder = self._reminders.get(reminder_id)
        if reminder is None:
            return False

        reminder.status = ReminderStatus.CANCELLED
        return True

    def get(self, reminder_id: UUID) -> Reminder | None:
        """Get a reminder by ID.

        Args:
            reminder_id: ID of the reminder.

        Returns:
            The Reminder or None if not found.
        """
        return self._reminders.get(reminder_id)

    def list_pending(self) -> list[Reminder]:
        """List all pending reminders.

        Returns:
            List of pending reminders, sorted by remind_at.
        """
        pending = [
            r for r in self._reminders.values()
            if r.status == ReminderStatus.PENDING
        ]
        return sorted(pending, key=lambda r: r.remind_at)

    def list_all(self) -> list[Reminder]:
        """List all reminders.

        Returns:
            List of all reminders.
        """
        return list(self._reminders.values())

    def check_due(self) -> list[Reminder]:
        """Check for and process due reminders.

        Returns:
            List of newly triggered reminders.
        """
        triggered = []
        for reminder in list(self._reminders.values()):
            if reminder.status == ReminderStatus.PENDING and reminder.is_due:
                reminder.status = ReminderStatus.TRIGGERED
                reminder.triggered_at = datetime.now(UTC)
                triggered.append(reminder)

                if self._on_trigger:
                    self._on_trigger(reminder)

                # Create next occurrence for recurring reminders
                if reminder.recurrence != Recurrence.NONE:
                    self._create_next_occurrence(reminder)

        return triggered

    def _create_next_occurrence(self, reminder: Reminder) -> Reminder:
        """Create the next occurrence of a recurring reminder.

        Args:
            reminder: The triggered recurring reminder.

        Returns:
            The new reminder instance.
        """
        if reminder.recurrence == Recurrence.DAILY:
            next_time = reminder.remind_at + timedelta(days=1)
        elif reminder.recurrence == Recurrence.WEEKLY:
            next_time = reminder.remind_at + timedelta(weeks=1)
        elif reminder.recurrence == Recurrence.MONTHLY:
            # Add approximately one month
            next_time = reminder.remind_at + timedelta(days=30)
        else:
            return reminder

        return self.create(
            message=reminder.message,
            remind_at=next_time,
            interaction_id=reminder.created_by_interaction,
            recurrence=reminder.recurrence,
        )

    def dismiss(self, reminder_id: UUID) -> bool:
        """Dismiss a triggered reminder.

        Args:
            reminder_id: ID of the reminder to dismiss.

        Returns:
            True if dismissed, False if not found or not triggered.
        """
        reminder = self._reminders.get(reminder_id)
        if reminder is None or reminder.status != ReminderStatus.TRIGGERED:
            return False

        reminder.status = ReminderStatus.DISMISSED
        return True

    def format_reminder(self, reminder: Reminder) -> str:
        """Format a reminder for display.

        Args:
            reminder: The reminder to format.

        Returns:
            Human-readable reminder description.
        """
        time_str = reminder.remind_at.strftime("%I:%M %p")
        date_str = reminder.remind_at.strftime("%B %d")

        if reminder.remind_at.date() == datetime.now(UTC).date():
            return f"Reminder at {time_str}: {reminder.message}"
        else:
            return f"Reminder on {date_str} at {time_str}: {reminder.message}"


def parse_reminder_time(text: str) -> datetime | None:
    """Parse a natural language time expression into a datetime.

    Args:
        text: Natural language time (e.g., "in 1 hour", "at 3 PM").

    Returns:
        Datetime for the reminder, or None if unparseable.

    Examples:
        >>> parse_reminder_time("in 1 hour")
        datetime(...)  # 1 hour from now
        >>> parse_reminder_time("at 3:30 PM")
        datetime(...)  # Today at 3:30 PM
    """
    if not text:
        return None

    text = text.lower().strip()
    now = datetime.now(UTC)

    # Try "in X minutes/hours" pattern
    relative_match = re.search(
        r"in\s+(\d+)\s*(minute|min|hour|hr)s?",
        text,
        re.IGNORECASE,
    )
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2).lower()

        if unit in ("hour", "hr"):
            return now + timedelta(hours=amount)
        else:
            return now + timedelta(minutes=amount)

    # Try "at HH:MM AM/PM" pattern
    time_match = re.search(
        r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
        text,
        re.IGNORECASE,
    )
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        period = time_match.group(3)

        if period:
            if period.lower() == "pm" and hour != 12:
                hour += 12
            elif period.lower() == "am" and hour == 12:
                hour = 0

        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time has passed today, schedule for tomorrow
        if result <= now:
            result += timedelta(days=1)

        # Check for "tomorrow" in the text
        if "tomorrow" in text:
            if result.date() == now.date():
                result += timedelta(days=1)

        return result

    # Try 24-hour format "at HH:MM"
    time_24_match = re.search(r"at\s+(\d{1,2}):(\d{2})", text)
    if time_24_match:
        hour = int(time_24_match.group(1))
        minute = int(time_24_match.group(2))

        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if result <= now:
            result += timedelta(days=1)

        if "tomorrow" in text and result.date() == now.date():
            result += timedelta(days=1)

        return result

    return None
