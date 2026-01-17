"""
Contract: AudioPlayback Protocol Extensions

Extends the existing AudioPlayback protocol with interrupt support.
These methods will be added to the existing playback implementations.
"""

from typing import Protocol


class InterruptiblePlayback(Protocol):
    """
    Extended playback protocol with interrupt support.

    Inherits all existing AudioPlayback methods and adds:
    - is_playing property for state checking
    - Guaranteed stop() behavior for interrupt handling
    """

    @property
    def is_playing(self) -> bool:
        """
        Return True if audio is currently being played.

        Thread-safe property that can be checked from any thread.
        """
        ...

    def play(self, audio: bytes, sample_rate: int) -> None:
        """
        Play audio synchronously (blocks until complete or stopped).

        Existing method - no changes to signature.
        """
        ...

    def play_async(self, audio: bytes, sample_rate: int) -> None:
        """
        Play audio asynchronously in background thread.

        Existing method - no changes to signature.
        """
        ...

    def stop(self) -> None:
        """
        Stop current playback immediately.

        Requirements for interrupt support:
        - MUST complete within 500ms (TTS_STOP_TIMEOUT_MS)
        - MUST be safe to call from any thread
        - MUST be idempotent (safe to call multiple times)
        - MUST set is_playing to False before returning
        """
        ...

    def play_tone(self, frequency: int, duration_ms: int) -> None:
        """
        Play a simple tone (for feedback sounds).

        Existing method - no changes to signature.
        """
        ...
