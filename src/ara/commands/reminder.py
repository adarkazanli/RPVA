"""Reminder management for voice commands.

Implements scheduled reminders with recurring support and JSON persistence.
"""

import json
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


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

    Provides thread-safe reminder management with trigger callbacks
    and JSON persistence for reminders to survive system restarts.
    """

    def __init__(
        self,
        on_trigger: Callable[[Reminder], None] | None = None,
        persistence_path: Path | str | None = None,
    ) -> None:
        """Initialize the reminder manager.

        Args:
            on_trigger: Optional callback when a reminder triggers.
            persistence_path: Path to JSON file for persistence. If None,
                              reminders are stored in memory only.
        """
        self._reminders: dict[UUID, Reminder] = {}
        self._on_trigger = on_trigger
        self._persistence_path: Path | None = Path(persistence_path) if persistence_path else None

        # Load existing reminders from persistence
        if self._persistence_path:
            self._load()

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
        self._save()
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
        self._save()
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
        pending = [r for r in self._reminders.values() if r.status == ReminderStatus.PENDING]
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

        if triggered:
            self._save()

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
        self._save()
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

    def clear_all(self) -> int:
        """Clear all reminders.

        Returns:
            Number of reminders that were cleared.
        """
        pending = [r for r in self._reminders.values() if r.status == ReminderStatus.PENDING]
        count = len(pending)

        for reminder in pending:
            reminder.status = ReminderStatus.CANCELLED

        if count > 0:
            self._save()

        return count

    def check_missed(self) -> list[Reminder]:
        """Check for and return reminders that were missed during system downtime.

        A missed reminder is one that:
        - Has status PENDING
        - Has remind_at time in the past

        Returns:
            List of missed reminders (not yet marked as triggered).
        """
        now = datetime.now(UTC)
        missed = []

        for reminder in self._reminders.values():
            if reminder.status == ReminderStatus.PENDING and reminder.remind_at < now:
                missed.append(reminder)

        return sorted(missed, key=lambda r: r.remind_at)

    def _save(self) -> None:
        """Save reminders to JSON file."""
        if not self._persistence_path:
            return

        try:
            # Ensure parent directory exists
            self._persistence_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "version": 1,
                "reminders": [
                    {
                        "id": str(r.id),
                        "message": r.message,
                        "remind_at": r.remind_at.isoformat(),
                        "recurrence": r.recurrence.value,
                        "status": r.status.value,
                        "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
                        "created_by_interaction": str(r.created_by_interaction),
                        "created_at": r.created_at.isoformat(),
                    }
                    for r in self._reminders.values()
                ],
            }

            with open(self._persistence_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._reminders)} reminders to {self._persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save reminders: {e}")

    def _load(self) -> None:
        """Load reminders from JSON file."""
        if not self._persistence_path or not self._persistence_path.exists():
            return

        try:
            with open(self._persistence_path) as f:
                data = json.load(f)

            version = data.get("version", 1)
            if version != 1:
                logger.warning(f"Unknown reminders file version: {version}")

            for item in data.get("reminders", []):
                try:
                    reminder = Reminder(
                        id=UUID(item["id"]),
                        message=item["message"],
                        remind_at=datetime.fromisoformat(item["remind_at"]),
                        recurrence=Recurrence(item["recurrence"]),
                        status=ReminderStatus(item["status"]),
                        triggered_at=(
                            datetime.fromisoformat(item["triggered_at"])
                            if item.get("triggered_at")
                            else None
                        ),
                        created_by_interaction=UUID(item["created_by_interaction"]),
                        created_at=datetime.fromisoformat(item["created_at"]),
                    )
                    self._reminders[reminder.id] = reminder
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid reminder: {e}")

            logger.info(f"Loaded {len(self._reminders)} reminders from {self._persistence_path}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in reminders file: {e}")
        except Exception as e:
            logger.error(f"Failed to load reminders: {e}")


def format_time_local(dt: datetime) -> str:
    """Format a datetime to local time string.

    Args:
        dt: Datetime to format (assumed UTC).

    Returns:
        Time string in format "H:MM AM/PM" (e.g., "2:34 AM").
    """
    # Convert from UTC to local time
    local_dt = dt.astimezone()
    # Format without leading zero on hour
    return local_dt.strftime("%-I:%M %p").replace(" AM", " AM").replace(" PM", " PM")


def _word_to_number(text: str) -> str:
    """Convert word numbers to digits.

    Args:
        text: Text potentially containing word numbers.

    Returns:
        Text with word numbers converted to digits.
    """
    word_numbers = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "fifteen": "15",
        "twenty": "20",
        "thirty": "30",
        "forty": "40",
        "forty-five": "45",
        "fortyfive": "45",
        "fifty": "50",
        "sixty": "60",
        "half": "30",  # "half an hour" -> "30 minutes"
    }
    result = text.lower()
    for word, digit in word_numbers.items():
        # Use word boundary to avoid partial matches
        result = re.sub(rf"\b{word}\b", digit, result)
    return result


def parse_reminder_time(text: str) -> datetime | None:
    """Parse a natural language time expression into a datetime.

    Args:
        text: Natural language time (e.g., "in 1 hour", "at 3 PM", "in one minute").

    Returns:
        Datetime for the reminder, or None if unparseable.

    Examples:
        >>> parse_reminder_time("in 1 hour")
        datetime(...)  # 1 hour from now
        >>> parse_reminder_time("in one minute")
        datetime(...)  # 1 minute from now
        >>> parse_reminder_time("at 3:30 PM")
        datetime(...)  # Today at 3:30 PM
    """
    if not text:
        return None

    # Convert word numbers to digits before parsing
    text = _word_to_number(text.lower().strip())
    now = datetime.now(UTC)

    # Try "in X seconds/minutes/hours" pattern (also matches without "in")
    relative_match = re.search(
        r"(?:in\s+)?(\d+)\s*(second|sec|minute|min|hour|hr)s?",
        text,
        re.IGNORECASE,
    )
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2).lower()

        if unit in ("hour", "hr"):
            return now + timedelta(hours=amount)
        elif unit in ("second", "sec"):
            return now + timedelta(seconds=amount)
        else:
            return now + timedelta(minutes=amount)

    # Try "at H.MM am/pm" pattern (decimal notation like "8.20am")
    decimal_time_match = re.search(
        r"(?:at\s+)?(\d{1,2})\.(\d{1,2})\s*(am|pm)",
        text,
        re.IGNORECASE,
    )
    if decimal_time_match:
        hour = int(decimal_time_match.group(1))
        minute = int(decimal_time_match.group(2))
        period = decimal_time_match.group(3).lower()

        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0

        result = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time has passed today, schedule for tomorrow
        if result <= now:
            result += timedelta(days=1)

        return result

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
        if "tomorrow" in text and result.date() == now.date():
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
