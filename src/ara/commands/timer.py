"""Timer management for voice commands.

Implements countdown timers with alert capabilities.
"""

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from uuid import UUID


class TimerStatus(Enum):
    """Status of a timer."""

    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class Timer:
    """A countdown timer with alert capability.

    Attributes:
        id: Unique timer identifier.
        name: Optional user-assigned name.
        duration_seconds: Total timer duration in seconds.
        started_at: When the timer was started.
        expires_at: When the timer will expire.
        status: Current timer status.
        alert_played: Whether the alert has been triggered.
        created_by_interaction: ID of the interaction that created this timer.
    """

    id: UUID
    name: str | None
    duration_seconds: int
    started_at: datetime
    expires_at: datetime
    status: TimerStatus
    alert_played: bool
    created_by_interaction: UUID
    _paused_at: datetime | None = field(default=None, repr=False)
    _remaining_when_paused: int | None = field(default=None, repr=False)

    @property
    def remaining_seconds(self) -> int:
        """Calculate remaining seconds on the timer."""
        if self.status == TimerStatus.PAUSED and self._remaining_when_paused is not None:
            return self._remaining_when_paused

        if self.status in (TimerStatus.COMPLETED, TimerStatus.CANCELLED):
            return 0

        now = datetime.now(UTC)
        remaining = (self.expires_at - now).total_seconds()
        return max(0, int(remaining))

    @property
    def is_expired(self) -> bool:
        """Check if the timer has expired."""
        if self.status != TimerStatus.RUNNING:
            return False
        return datetime.now(UTC) >= self.expires_at


class TimerManager:
    """Manages timers with create, cancel, query operations.

    Provides thread-safe timer management with expiration callbacks.
    """

    def __init__(self, on_expire: Callable[[Timer], None] | None = None) -> None:
        """Initialize the timer manager.

        Args:
            on_expire: Optional callback when a timer expires.
        """
        self._timers: dict[UUID, Timer] = {}
        self._on_expire = on_expire

    def create(
        self,
        duration_seconds: int,
        interaction_id: UUID,
        name: str | None = None,
    ) -> Timer:
        """Create a new timer.

        Args:
            duration_seconds: Duration in seconds.
            interaction_id: ID of the creating interaction.
            name: Optional timer name.

        Returns:
            The created Timer object.
        """
        now = datetime.now(UTC)
        timer = Timer(
            id=uuid.uuid4(),
            name=name,
            duration_seconds=duration_seconds,
            started_at=now,
            expires_at=now + timedelta(seconds=duration_seconds),
            status=TimerStatus.RUNNING,
            alert_played=False,
            created_by_interaction=interaction_id,
        )
        self._timers[timer.id] = timer
        return timer

    def cancel(self, timer_id: UUID) -> bool:
        """Cancel a timer.

        Args:
            timer_id: ID of the timer to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        timer = self._timers.get(timer_id)
        if timer is None:
            return False

        timer.status = TimerStatus.CANCELLED
        return True

    def get(self, timer_id: UUID) -> Timer | None:
        """Get a timer by ID.

        Args:
            timer_id: ID of the timer.

        Returns:
            The Timer or None if not found.
        """
        return self._timers.get(timer_id)

    def get_by_name(self, name: str) -> Timer | None:
        """Get a timer by name.

        Args:
            name: Name of the timer.

        Returns:
            The Timer or None if not found.
        """
        name_lower = name.lower()
        for timer in self._timers.values():
            if timer.name and timer.name.lower() == name_lower:
                if timer.status == TimerStatus.RUNNING:
                    return timer
        return None

    def list_active(self) -> list[Timer]:
        """List all active (running or paused) timers.

        Returns:
            List of active timers.
        """
        return [
            t for t in self._timers.values()
            if t.status in (TimerStatus.RUNNING, TimerStatus.PAUSED)
        ]

    def list_all(self) -> list[Timer]:
        """List all timers.

        Returns:
            List of all timers.
        """
        return list(self._timers.values())

    def check_expired(self) -> list[Timer]:
        """Check for and process expired timers.

        Returns:
            List of newly expired timers.
        """
        expired = []
        for timer in self._timers.values():
            if timer.status == TimerStatus.RUNNING and timer.is_expired:
                timer.status = TimerStatus.COMPLETED
                timer.alert_played = True
                expired.append(timer)

                if self._on_expire:
                    self._on_expire(timer)

        return expired

    def pause(self, timer_id: UUID) -> bool:
        """Pause a running timer.

        Args:
            timer_id: ID of the timer to pause.

        Returns:
            True if paused, False if not found or not running.
        """
        timer = self._timers.get(timer_id)
        if timer is None or timer.status != TimerStatus.RUNNING:
            return False

        timer._remaining_when_paused = timer.remaining_seconds
        timer._paused_at = datetime.now(UTC)
        timer.status = TimerStatus.PAUSED
        return True

    def resume(self, timer_id: UUID) -> bool:
        """Resume a paused timer.

        Args:
            timer_id: ID of the timer to resume.

        Returns:
            True if resumed, False if not found or not paused.
        """
        timer = self._timers.get(timer_id)
        if timer is None or timer.status != TimerStatus.PAUSED:
            return False

        if timer._remaining_when_paused is not None:
            timer.expires_at = datetime.now(UTC) + timedelta(
                seconds=timer._remaining_when_paused
            )

        timer._remaining_when_paused = None
        timer._paused_at = None
        timer.status = TimerStatus.RUNNING
        return True

    def format_remaining(self, timer: Timer) -> str:
        """Format remaining time as human-readable string.

        Args:
            timer: The timer to format.

        Returns:
            Human-readable remaining time.
        """
        seconds = timer.remaining_seconds

        if seconds <= 0:
            return "expired"

        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs > 0 and hours == 0:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")

        return " and ".join(parts) if parts else "less than a second"


def parse_duration(text: str) -> int | None:
    """Parse a natural language duration into seconds.

    Args:
        text: Natural language duration (e.g., "5 minutes", "1 hour").

    Returns:
        Duration in seconds, or None if unparseable.

    Examples:
        >>> parse_duration("5 minutes")
        300
        >>> parse_duration("1 hour and 30 minutes")
        5400
    """
    if not text:
        return None

    text = text.lower().strip()
    total_seconds = 0
    found_match = False

    # Patterns for different time units
    patterns = [
        (r"(\d+)\s*(?:hour|hr)s?", 3600),
        (r"(\d+)\s*(?:minute|min)s?", 60),
        (r"(\d+)\s*(?:second|sec)s?", 1),
    ]

    for pattern, multiplier in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            total_seconds += int(match) * multiplier
            found_match = True

    # If no pattern matched, try parsing as just a number (assume minutes)
    if not found_match:
        try:
            number = int(re.search(r"(\d+)", text).group(1))
            return number * 60  # Assume minutes
        except (AttributeError, ValueError):
            return None

    return total_seconds if total_seconds > 0 else None
