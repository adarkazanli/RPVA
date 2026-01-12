"""Mock transcriber for testing.

Provides a controllable mock implementation for unit and integration testing.
"""

import time
from collections.abc import Iterator

from .transcriber import PartialTranscription, TranscriptionResult


class MockTranscriber:
    """Mock transcriber for testing.

    Allows setting predetermined responses for predictable testing.
    """

    def __init__(self) -> None:
        """Initialize mock transcriber."""
        self._language: str = "en"
        self._response_text: str = ""
        self._response_confidence: float = 0.0
        self._call_count: int = 0
        self._error_message: str | None = None
        self._latency_ms: int = 50  # Simulated latency

    def set_response(self, text: str, confidence: float = 0.95) -> None:
        """Set the response to return on next transcription.

        Args:
            text: Text to return
            confidence: Confidence score to return
        """
        self._response_text = text
        self._response_confidence = confidence
        self._error_message = None

    def set_error(self, message: str) -> None:
        """Set an error to raise on next transcription.

        Args:
            message: Error message
        """
        self._error_message = message

    def set_latency(self, latency_ms: int) -> None:
        """Set simulated latency.

        Args:
            latency_ms: Latency in milliseconds
        """
        self._latency_ms = latency_ms

    def transcribe(self, audio: bytes, sample_rate: int) -> TranscriptionResult:
        """Return preset transcription result."""
        self._call_count += 1

        if self._error_message:
            raise RuntimeError(self._error_message)

        # Simulate latency
        time.sleep(self._latency_ms / 1000)

        # Calculate audio duration
        duration_ms = int(len(audio) / (sample_rate * 2) * 1000)

        return TranscriptionResult(
            text=self._response_text,
            confidence=self._response_confidence,
            language=self._language,
            duration_ms=duration_ms,
            segments=[],
        )

    def transcribe_stream(
        self, audio_stream: Iterator[bytes]
    ) -> Iterator[PartialTranscription]:
        """Yield mock partial transcriptions."""
        # Consume the stream
        for _ in audio_stream:
            pass

        # Return the preset response as a final result
        if self._response_text:
            words = self._response_text.split()
            for i, word in enumerate(words):
                yield PartialTranscription(
                    text=" ".join(words[: i + 1]),
                    is_final=(i == len(words) - 1),
                )

    def set_language(self, language: str) -> None:
        """Set language."""
        self._language = language

    @property
    def language(self) -> str:
        """Get current language setting."""
        return self._language

    @property
    def call_count(self) -> int:
        """Get number of transcribe calls."""
        return self._call_count

    def clear(self) -> None:
        """Reset mock state."""
        self._response_text = ""
        self._response_confidence = 0.0
        self._call_count = 0
        self._error_message = None


__all__ = ["MockTranscriber"]
