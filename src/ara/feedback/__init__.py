"""Feedback module for Ara Voice Assistant.

Provides audio feedback (beeps, chimes) for system events like
wake word detection, errors, and mode changes.
"""

from enum import Enum
from typing import Protocol


class FeedbackType(Enum):
    """Types of audio feedback events."""

    WAKE_WORD_DETECTED = "wake"
    PROCESSING = "processing"
    ERROR = "error"
    MODE_CHANGE = "mode_change"
    TIMER_ALERT = "timer_alert"
    REMINDER_ALERT = "reminder_alert"
    SUCCESS = "success"
    INTERRUPT_ACKNOWLEDGED = "interrupt_ack"
    THINKING = "thinking"  # Looping chime while waiting for LLM
    RESPONSE_COMPLETE = "response_complete"  # Long beep at end of interaction


class AudioFeedback(Protocol):
    """Interface for audio feedback sounds.

    Implementations play appropriate sounds for different system events
    to provide auditory feedback to users.
    """

    def play(self, feedback_type: FeedbackType, *, blocking: bool = False) -> None:
        """Play feedback sound for the given event type.

        Args:
            feedback_type: The type of event to provide feedback for
            blocking: If True, wait for playback to complete before returning
        """
        ...

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable feedback sounds.

        Args:
            enabled: True to enable sounds, False to disable
        """
        ...

    @property
    def is_enabled(self) -> bool:
        """Return True if feedback sounds are enabled."""
        ...


__all__ = [
    "AudioFeedback",
    "FeedbackType",
]
