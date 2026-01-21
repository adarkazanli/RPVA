"""Waiting indicator for long-running operations.

Provides looping audio feedback while waiting for Claude responses.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from . import FeedbackType

if TYPE_CHECKING:
    from . import AudioFeedback

logger = logging.getLogger(__name__)


class WaitingIndicator:
    """Plays looping audio feedback while waiting for a response.

    Used to provide audio feedback during Claude API calls to indicate
    that the system is waiting for a response.

    Usage:
        indicator = WaitingIndicator(feedback)
        indicator.start()
        # ... do work ...
        indicator.stop()

    Or as context manager:
        with WaitingIndicator(feedback):
            # ... do work ...
    """

    def __init__(
        self,
        feedback: AudioFeedback,
        loop_interval: float = 1.0,
    ) -> None:
        """Initialize waiting indicator.

        Args:
            feedback: AudioFeedback instance for playing sounds.
            loop_interval: Seconds between loop iterations.
        """
        self._feedback = feedback
        self._loop_interval = loop_interval
        self._playing = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        """Return True if the indicator is currently playing."""
        return self._playing

    def start(self) -> None:
        """Start the waiting indicator loop.

        This method is idempotent - calling it multiple times while
        already playing has no effect.
        """
        with self._lock:
            if self._playing:
                return

            if not self._feedback.is_enabled:
                return

            self._playing = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._play_loop,
                daemon=True,
                name="claude-waiting-indicator",
            )
            self._thread.start()
            logger.debug("Waiting indicator started")

    def stop(self) -> None:
        """Stop the waiting indicator loop.

        This method is idempotent - calling it multiple times or
        without starting has no effect.
        """
        with self._lock:
            if not self._playing:
                return

            self._stop_event.set()
            self._playing = False

            if self._thread is not None:
                self._thread.join(timeout=2.0)
                self._thread = None

            logger.debug("Waiting indicator stopped")

    def _play_loop(self) -> None:
        """Internal loop that plays the waiting sound repeatedly."""
        while not self._stop_event.is_set():
            try:
                self._feedback.play(FeedbackType.CLAUDE_WAITING, blocking=True)
            except Exception as e:
                logger.warning(f"Error playing waiting sound: {e}")

            # Wait for interval or stop signal
            if self._stop_event.wait(timeout=self._loop_interval):
                break

    def __enter__(self) -> WaitingIndicator:
        """Context manager entry - starts the indicator."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - stops the indicator."""
        self.stop()


__all__ = ["WaitingIndicator"]
