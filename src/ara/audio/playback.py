"""Audio playback protocol and data classes.

Defines the interface for audio output playback that all platform
implementations must follow.
"""

from typing import Protocol


class AudioPlayback(Protocol):
    """Interface for audio output playback.

    Platform-specific implementations (macOS, Linux, Pi) must implement
    this protocol to enable seamless cross-platform audio playback.
    """

    def play(self, audio: bytes, sample_rate: int) -> None:
        """Play audio data synchronously.

        Blocks until playback is complete.

        Args:
            audio: Raw PCM audio bytes (16-bit, mono)
            sample_rate: Sample rate in Hz

        Raises:
            RuntimeError: If playback fails
        """
        ...

    def play_async(self, audio: bytes, sample_rate: int) -> None:
        """Play audio data asynchronously.

        Returns immediately while audio plays in background.

        Args:
            audio: Raw PCM audio bytes (16-bit, mono)
            sample_rate: Sample rate in Hz

        Raises:
            RuntimeError: If playback cannot be started
        """
        ...

    def stop(self) -> None:
        """Stop current playback.

        Safe to call even if nothing is playing.
        """
        ...

    def play_tone(self, frequency: int, duration_ms: int) -> None:
        """Play a simple tone for feedback.

        Args:
            frequency: Tone frequency in Hz
            duration_ms: Duration in milliseconds

        Raises:
            RuntimeError: If playback fails
        """
        ...

    @property
    def is_playing(self) -> bool:
        """Return True if audio is currently playing."""
        ...

    @property
    def sample_rate(self) -> int:
        """Get the configured output sample rate in Hz."""
        ...


__all__ = ["AudioPlayback"]
