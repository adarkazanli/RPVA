"""Synthesizer protocol and data classes.

Defines the interface for text-to-speech synthesis.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SynthesisResult:
    """Result of text-to-speech synthesis.

    Attributes:
        audio: Raw PCM audio bytes
        sample_rate: Audio sample rate in Hz
        duration_ms: Audio duration in milliseconds
        latency_ms: Synthesis latency in milliseconds
    """

    audio: bytes
    sample_rate: int
    duration_ms: int
    latency_ms: int


class Synthesizer(Protocol):
    """Interface for text-to-speech synthesis.

    Implementations convert text to speech audio.
    """

    def synthesize(self, text: str) -> SynthesisResult:
        """Convert text to speech audio.

        Args:
            text: Text to synthesize

        Returns:
            SynthesisResult with audio data

        Raises:
            RuntimeError: If synthesis fails
        """
        ...

    def set_voice(self, voice_id: str) -> None:
        """Set the voice to use for synthesis.

        Args:
            voice_id: Voice identifier
        """
        ...

    def set_speed(self, speed: float) -> None:
        """Set speech speed.

        Args:
            speed: Speed multiplier (1.0 = normal)
        """
        ...

    def get_available_voices(self) -> list[str]:
        """Return list of available voice IDs."""
        ...


__all__ = ["Synthesizer", "SynthesisResult"]
