"""Interrupt handling module for speech interrupt and reprocessing.

Provides state machine, request buffer, and continuation window management
for handling user speech interrupts during agent responses.
"""

import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..audio.capture import AudioCapture
    from ..audio.playback import AudioPlayback
    from ..stt.transcriber import Transcriber

# Constants
INTERRUPT_THRESHOLD: float = 750.0  # RMS energy threshold to trigger interrupt
SILENCE_TIMEOUT_MS: int = 2000  # Milliseconds of silence before reprocessing
CONTINUATION_WINDOW_S: float = 5.0  # Seconds after response to accept continuations
TTS_STOP_TIMEOUT_MS: int = 500  # Maximum time to stop TTS playback
INTERRUPT_FEEDBACK_FREQ: int = 200  # Hz frequency for interrupt acknowledgment tone
INTERRUPT_FEEDBACK_MS: int = 100  # Duration of interrupt acknowledgment tone

# Special keywords that indicate intent change
SPECIAL_KEYWORDS = frozenset(
    {
        "stop",
        "wait",
        "cancel",
        "never mind",
        "nevermind",
        "actually",
        "hold on",
    }
)


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


class RequestBuffer:
    """Accumulates user speech segments within a single conversation turn."""

    def __init__(self) -> None:
        """Initialize empty request buffer."""
        self._segments: list[BufferSegment] = []
        self._lock = threading.Lock()

    @property
    def segments(self) -> list[BufferSegment]:
        """Get all segments in order."""
        with self._lock:
            return self._segments.copy()

    @property
    def is_empty(self) -> bool:
        """Return True if no segments accumulated."""
        with self._lock:
            return len(self._segments) == 0

    def append(self, text: str, is_interrupt: bool = False) -> None:
        """Add a new segment with current timestamp."""
        segment = BufferSegment(
            text=text.strip(),
            timestamp=datetime.now(),
            is_interrupt=is_interrupt,
        )
        with self._lock:
            self._segments.append(segment)

    def get_combined_text(self) -> str:
        """Return all segments joined by space."""
        with self._lock:
            return " ".join(seg.text for seg in self._segments if seg.text)

    def clear(self) -> None:
        """Reset buffer for new conversation turn."""
        with self._lock:
            self._segments.clear()


class ContinuationWindow:
    """Manages the post-response continuation period."""

    def __init__(self, duration_seconds: float = CONTINUATION_WINDOW_S) -> None:
        """Initialize continuation window.

        Args:
            duration_seconds: Window duration in seconds (default 5.0)
        """
        self._duration = duration_seconds
        self._timer: threading.Timer | None = None
        self._is_active = False
        self._on_expire: Callable[[], None] | None = None
        self._lock = threading.Lock()

    @property
    def is_active(self) -> bool:
        """Return True if window is open and accepting input."""
        with self._lock:
            return self._is_active

    def start(self, on_expire: Callable[[], None] | None = None) -> None:
        """Begin countdown. Calls on_expire when window closes.

        Args:
            on_expire: Optional callback when window expires
        """
        with self._lock:
            self._cancel_timer_unsafe()
            self._on_expire = on_expire
            self._is_active = True
            self._timer = threading.Timer(self._duration, self._handle_expire)
            self._timer.daemon = True
            self._timer.start()

    def cancel(self) -> None:
        """Close window early."""
        with self._lock:
            self._cancel_timer_unsafe()
            self._is_active = False

    def reset(self) -> None:
        """Restart countdown."""
        with self._lock:
            callback = self._on_expire
        self.start(on_expire=callback)

    def _cancel_timer_unsafe(self) -> None:
        """Cancel timer without lock (must hold lock when calling)."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _handle_expire(self) -> None:
        """Handle window expiration."""
        with self._lock:
            self._is_active = False
            callback = self._on_expire

        if callback is not None:
            callback()


def is_special_keyword(text: str) -> bool:
    """Check if text contains a special interrupt keyword.

    Args:
        text: User speech text to check

    Returns:
        True if text is or contains a special keyword
    """
    text_lower = text.lower().strip()
    return text_lower in SPECIAL_KEYWORDS


def calculate_energy(audio_data: bytes) -> float:
    """Calculate RMS energy of audio data.

    Args:
        audio_data: Raw PCM audio bytes (16-bit, mono)

    Returns:
        RMS energy value
    """
    if len(audio_data) < 2:
        return 0.0

    # Convert to int16 samples
    num_samples = len(audio_data) // 2
    try:
        samples = struct.unpack(f"<{num_samples}h", audio_data)
    except struct.error:
        return 0.0

    # Calculate RMS energy
    if not samples:
        return 0.0

    sum_squares = sum(s * s for s in samples)
    rms = (sum_squares / num_samples) ** 0.5

    return float(rms)


class InterruptManager:
    """Manages speech interrupts during voice assistant interactions.

    Coordinates audio capture monitoring during TTS playback to detect
    user speech and manage the request buffer and continuation window.
    """

    def __init__(
        self,
        capture: "AudioCapture",
        playback: "AudioPlayback",
        transcriber: "Transcriber",
        energy_threshold: float = INTERRUPT_THRESHOLD,
        silence_timeout_ms: int = SILENCE_TIMEOUT_MS,
    ) -> None:
        """Initialize interrupt manager.

        Args:
            capture: Audio capture instance
            playback: Audio playback instance
            transcriber: Speech-to-text transcriber
            energy_threshold: RMS energy threshold for interrupt detection
            silence_timeout_ms: Silence duration to consider speech complete
        """
        self._capture = capture
        self._playback = playback
        self._transcriber = transcriber
        self._energy_threshold = energy_threshold
        self._silence_timeout_ms = silence_timeout_ms

        self._state = InterruptState.IDLE
        self._request_buffer = RequestBuffer()
        self._continuation_window = ContinuationWindow()

        self._monitoring = False
        self._monitor_thread: threading.Thread | None = None
        self._interrupt_event = threading.Event()
        self._interrupt_audio: bytes = b""
        self._interrupt_lock = threading.Lock()

    @property
    def state(self) -> InterruptState:
        """Get current state of the interrupt handler."""
        return self._state

    @property
    def request_buffer(self) -> RequestBuffer:
        """Get access to accumulated user input."""
        return self._request_buffer

    def set_initial_request(self, text: str) -> None:
        """Set the initial user request (before any interrupts).

        Args:
            text: Transcribed user speech
        """
        self._request_buffer.append(text, is_interrupt=False)
        self._state = InterruptState.LISTENING

    def start_monitoring(self) -> None:
        """Begin monitoring for user speech during response playback."""
        self._monitoring = True
        self._interrupt_event.clear()
        self._interrupt_audio = b""
        self._state = InterruptState.RESPONDING

        # Ensure capture is stopped before starting monitor thread
        if getattr(self._capture, 'is_active', False):
            self._capture.stop()
            time.sleep(0.1)  # Allow PyAudio to settle

        self._monitor_thread = threading.Thread(
            target=self._monitor_for_interrupt,
            daemon=True,
        )
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring and cleanup threads."""
        self._monitoring = False
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None

    def _monitor_for_interrupt(self) -> None:
        """Background thread to detect speech during playback."""
        # Small delay to avoid PyAudio segfault from rapid operations
        time.sleep(0.05)
        self._capture.start()
        try:
            for chunk in self._capture.stream():
                if not self._monitoring:
                    break

                energy = calculate_energy(chunk.data)

                if energy > self._energy_threshold:
                    # Interrupt detected
                    self._interrupt_event.set()
                    self._state = InterruptState.INTERRUPTED
                    with self._interrupt_lock:
                        self._interrupt_audio += chunk.data

                elif self._interrupt_event.is_set():
                    # Continue accumulating after interrupt
                    with self._interrupt_lock:
                        self._interrupt_audio += chunk.data
        finally:
            # Only stop capture if no interrupt was detected
            # If interrupt occurred, wait_for_interrupt_complete will handle capture
            if not self._interrupt_event.is_set():
                self._capture.stop()

    def play_with_monitoring(
        self,
        audio: bytes,
        sample_rate: int,
        on_interrupt: Callable[[InterruptEvent], None] | None = None,
    ) -> InterruptEvent | None:
        """Play audio while monitoring for user speech.

        Args:
            audio: TTS audio bytes to play
            sample_rate: Audio sample rate
            on_interrupt: Optional callback when interrupt detected

        Returns:
            InterruptEvent if user interrupted, None if playback completed normally
        """
        self.start_monitoring()

        # Play audio asynchronously
        self._playback.play_async(audio, sample_rate)

        # Wait for either playback completion or interrupt
        while self._playback.is_playing:
            if self._interrupt_event.is_set():
                # Stop playback immediately
                self._playback.stop()

                # Create interrupt event
                with self._interrupt_lock:
                    interrupt_audio = self._interrupt_audio

                event = InterruptEvent(
                    audio_data=interrupt_audio,
                    energy_level=self._energy_threshold,
                    detected_at=datetime.now(),
                    duration_ms=len(interrupt_audio) // 32,  # Approximate ms
                )

                if on_interrupt:
                    on_interrupt(event)

                self.stop_monitoring()
                return event

            time.sleep(0.05)  # Poll every 50ms

        self.stop_monitoring()
        return None

    def wait_for_interrupt_complete(self, timeout_ms: int = SILENCE_TIMEOUT_MS) -> str | None:
        """Wait for user to finish speaking after interrupt.

        Args:
            timeout_ms: Silence duration to consider speech complete

        Returns:
            Transcribed interrupt text, or None if timeout without speech
        """
        # Record remaining speech
        silence_start: float | None = None
        audio_buffer: list[bytes] = []

        with self._interrupt_lock:
            audio_buffer.append(self._interrupt_audio)

        # Only start capture if not already active (monitor thread may have left it running)
        capture_was_active = getattr(self._capture, 'is_active', False)
        if not capture_was_active:
            # Small delay to avoid PyAudio segfault from rapid stop/start
            time.sleep(0.1)
            self._capture.start()
        try:
            for chunk in self._capture.stream():
                energy = calculate_energy(chunk.data)
                audio_buffer.append(chunk.data)

                if energy < self._energy_threshold:
                    # Silence detected
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) * 1000 >= timeout_ms:
                        # Silence timeout reached
                        break
                else:
                    # Speech continuing
                    silence_start = None
        finally:
            self._capture.stop()

        # Transcribe the accumulated audio
        combined_audio = b"".join(audio_buffer)
        if not combined_audio:
            return None

        result = self._transcriber.transcribe(combined_audio, 16000)
        if result and result.text:
            # Append to buffer as interrupt
            self._request_buffer.append(result.text, is_interrupt=True)
            return result.text

        return None

    def get_combined_request(self) -> str:
        """Get all accumulated input as single string for reprocessing.

        Returns:
            Combined text from all segments
        """
        return self._request_buffer.get_combined_text()

    def start_continuation_window(
        self,
        on_expire: Callable[[], None] | None = None,
    ) -> None:
        """Start 5-second post-response window for user additions.

        Args:
            on_expire: Callback when window expires
        """
        self._state = InterruptState.CONTINUATION
        self._continuation_window.start(on_expire=on_expire)

    def cancel_continuation_window(self) -> None:
        """Cancel continuation window (user spoke or new request)."""
        self._continuation_window.cancel()

    def reset(self) -> None:
        """Reset all state for new conversation turn."""
        self.stop_monitoring()
        self._continuation_window.cancel()
        self._request_buffer.clear()
        self._interrupt_event.clear()
        self._interrupt_audio = b""
        self._state = InterruptState.IDLE


__all__ = [
    "BufferSegment",
    "ContinuationWindow",
    "InterruptEvent",
    "InterruptManager",
    "InterruptState",
    "RequestBuffer",
    "calculate_energy",
    "is_special_keyword",
    "CONTINUATION_WINDOW_S",
    "INTERRUPT_FEEDBACK_FREQ",
    "INTERRUPT_FEEDBACK_MS",
    "INTERRUPT_THRESHOLD",
    "SILENCE_TIMEOUT_MS",
    "TTS_STOP_TIMEOUT_MS",
]
