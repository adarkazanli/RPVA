"""
Contract: InterruptManager Protocol

Defines the interface for managing speech interrupts during voice assistant responses.
This is a design contract - implementation will follow this specification.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Callable, Protocol


class InterruptState(Enum):
    """State machine for interrupt handling."""

    IDLE = auto()  # Waiting for wake word
    LISTENING = auto()  # Recording initial request
    PROCESSING = auto()  # Running STT/intent/LLM
    RESPONDING = auto()  # TTS playback, monitoring for interrupts
    INTERRUPTED = auto()  # User spoke, accumulating input
    CONTINUATION = auto()  # Post-response window


@dataclass
class BufferSegment:
    """Single speech segment in the request buffer."""

    text: str
    timestamp: datetime
    is_interrupt: bool = False


@dataclass
class InterruptEvent:
    """Captured interrupt audio and metadata."""

    audio_data: bytes
    energy_level: float
    detected_at: datetime
    duration_ms: int


class RequestBuffer(Protocol):
    """Protocol for accumulating user speech segments."""

    @property
    def segments(self) -> list[BufferSegment]:
        """All segments in order."""
        ...

    @property
    def is_empty(self) -> bool:
        """True if no segments accumulated."""
        ...

    def append(self, text: str, is_interrupt: bool = False) -> None:
        """Add a new segment with current timestamp."""
        ...

    def get_combined_text(self) -> str:
        """Return all segments joined by space."""
        ...

    def clear(self) -> None:
        """Reset buffer for new conversation turn."""
        ...


class ContinuationWindow(Protocol):
    """Protocol for managing post-response continuation period."""

    @property
    def is_active(self) -> bool:
        """True if window is open and accepting input."""
        ...

    def start(self, on_expire: Callable[[], None] | None = None) -> None:
        """Begin 5-second countdown. Calls on_expire when window closes."""
        ...

    def cancel(self) -> None:
        """Close window early."""
        ...

    def reset(self) -> None:
        """Restart 5-second countdown."""
        ...


class InterruptManager(Protocol):
    """
    Protocol for managing speech interrupts during voice assistant interactions.

    Usage:
        manager = create_interrupt_manager(capture, playback)

        # Start monitoring during response
        manager.start_monitoring()

        # Play response while monitoring for interrupts
        interrupt = manager.play_with_monitoring(tts_audio, sample_rate)

        if interrupt:
            # User interrupted - get combined request
            combined = manager.get_combined_request()
            # Reprocess with new intent
            ...

        # After response completes without interrupt
        manager.start_continuation_window()

        # When window expires or new conversation starts
        manager.reset()
    """

    @property
    def state(self) -> InterruptState:
        """Current state of the interrupt handler."""
        ...

    @property
    def request_buffer(self) -> RequestBuffer:
        """Access to accumulated user input."""
        ...

    def set_initial_request(self, text: str) -> None:
        """Set the initial user request (before any interrupts)."""
        ...

    def start_monitoring(self) -> None:
        """Begin monitoring for user speech during response playback."""
        ...

    def stop_monitoring(self) -> None:
        """Stop monitoring and cleanup threads."""
        ...

    def play_with_monitoring(
        self,
        audio: bytes,
        sample_rate: int,
        on_interrupt: Callable[[InterruptEvent], None] | None = None,
    ) -> InterruptEvent | None:
        """
        Play audio while monitoring for user speech.

        Args:
            audio: TTS audio bytes to play
            sample_rate: Audio sample rate
            on_interrupt: Optional callback when interrupt detected

        Returns:
            InterruptEvent if user interrupted, None if playback completed normally
        """
        ...

    def wait_for_interrupt_complete(self, timeout_ms: int = 2000) -> str | None:
        """
        Wait for user to finish speaking after interrupt.

        Args:
            timeout_ms: Silence duration to consider speech complete

        Returns:
            Transcribed interrupt text, or None if timeout without speech
        """
        ...

    def get_combined_request(self) -> str:
        """Get all accumulated input as single string for reprocessing."""
        ...

    def start_continuation_window(
        self, on_expire: Callable[[], None] | None = None
    ) -> None:
        """Start 5-second post-response window for user additions."""
        ...

    def cancel_continuation_window(self) -> None:
        """Cancel continuation window (user spoke or new request)."""
        ...

    def reset(self) -> None:
        """Reset all state for new conversation turn."""
        ...


# Constants (part of contract)
INTERRUPT_THRESHOLD: float = 750.0
SILENCE_TIMEOUT_MS: int = 2000
CONTINUATION_WINDOW_S: float = 5.0
TTS_STOP_TIMEOUT_MS: int = 500
INTERRUPT_FEEDBACK_FREQ: int = 200
INTERRUPT_FEEDBACK_MS: int = 100
