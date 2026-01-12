"""Audio capture protocol and data classes.

Defines the interface for audio input capture that all platform
implementations must follow.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


@dataclass
class AudioChunk:
    """Raw audio data chunk.

    Attributes:
        data: Raw PCM audio bytes
        sample_rate: Sample rate in Hz (e.g., 16000)
        channels: Number of audio channels (1=mono, 2=stereo)
        sample_width: Bytes per sample (2 for 16-bit audio)
        timestamp_ms: Timestamp when chunk was captured
    """

    data: bytes
    sample_rate: int
    channels: int
    sample_width: int
    timestamp_ms: int

    @property
    def duration_ms(self) -> float:
        """Calculate duration of this chunk in milliseconds."""
        if self.sample_rate == 0 or self.sample_width == 0 or self.channels == 0:
            return 0.0
        num_samples = len(self.data) / (self.sample_width * self.channels)
        return (num_samples / self.sample_rate) * 1000

    @property
    def num_frames(self) -> int:
        """Number of audio frames in this chunk."""
        if self.sample_width == 0 or self.channels == 0:
            return 0
        return len(self.data) // (self.sample_width * self.channels)


class AudioCapture(Protocol):
    """Interface for audio input capture.

    Platform-specific implementations (macOS, Linux, Pi) must implement
    this protocol to enable seamless cross-platform audio capture.
    """

    def start(self) -> None:
        """Start capturing audio from input device.

        Raises:
            RuntimeError: If capture cannot be started
        """
        ...

    def stop(self) -> None:
        """Stop capturing audio.

        Safe to call even if not currently capturing.
        """
        ...

    def read(self, frames: int) -> AudioChunk:
        """Read specified number of frames from buffer.

        Args:
            frames: Number of audio frames to read

        Returns:
            AudioChunk containing the requested frames

        Raises:
            RuntimeError: If not currently capturing
        """
        ...

    def stream(self) -> Iterator[AudioChunk]:
        """Yield audio chunks continuously.

        Yields:
            AudioChunk objects as audio is captured

        Note:
            This is a blocking iterator. Use in a separate thread
            if non-blocking behavior is needed.
        """
        ...

    @property
    def is_active(self) -> bool:
        """Return True if capture is currently active."""
        ...

    @property
    def sample_rate(self) -> int:
        """Get the configured sample rate in Hz."""
        ...

    @property
    def channels(self) -> int:
        """Get the number of channels."""
        ...

    @property
    def sample_width(self) -> int:
        """Get bytes per sample."""
        ...


__all__ = ["AudioCapture", "AudioChunk"]
