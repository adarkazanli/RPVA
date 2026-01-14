"""Transcriber protocol and data classes.

Defines the interface for speech-to-text transcription.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription.

    Attributes:
        text: Transcribed text
        confidence: Overall confidence score (0.0 to 1.0)
        language: Detected language code (e.g., "en")
        duration_ms: Duration of audio processed in milliseconds
        segments: Optional word-level timestamps
    """

    text: str
    confidence: float
    language: str
    duration_ms: int
    segments: list[dict] = field(default_factory=list)


@dataclass
class PartialTranscription:
    """Partial result during streaming transcription.

    Attributes:
        text: Partial transcribed text
        is_final: True if this is a final segment
    """

    text: str
    is_final: bool


class Transcriber(Protocol):
    """Interface for speech-to-text transcription.

    Implementations convert audio to text using various STT engines.
    """

    def transcribe(self, audio: bytes, sample_rate: int) -> TranscriptionResult:
        """Transcribe audio buffer to text.

        Args:
            audio: Raw PCM audio bytes (16-bit, mono)
            sample_rate: Audio sample rate in Hz

        Returns:
            TranscriptionResult with transcribed text

        Raises:
            RuntimeError: If transcription fails
        """
        ...

    def transcribe_stream(self, audio_stream: Iterator[bytes]) -> Iterator[PartialTranscription]:
        """Stream transcription results as audio arrives.

        Args:
            audio_stream: Iterator yielding audio chunks

        Yields:
            PartialTranscription results

        Note:
            Not all implementations support streaming.
        """
        ...

    def set_language(self, language: str) -> None:
        """Set expected language for transcription.

        Args:
            language: Language code (e.g., "en", "es", "fr")
        """
        ...


__all__ = ["PartialTranscription", "TranscriptionResult", "Transcriber"]
