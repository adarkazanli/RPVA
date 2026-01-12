"""Mock wake word detector for testing.

Provides a controllable mock implementation for unit and integration testing.
"""

from ..audio.capture import AudioChunk
from .detector import WakeWordResult


class MockWakeWordDetector:
    """Mock wake word detector for testing.

    Allows scheduling detections at specific chunk counts for predictable testing.
    """

    def __init__(self) -> None:
        """Initialize mock detector."""
        self._keywords: list[str] = []
        self._sensitivity: float = 0.5
        self._chunk_count: int = 0
        self._scheduled_detections: dict[int, float] = {}  # chunk_num -> confidence
        self._initialized: bool = False

    def initialize(self, keywords: list[str], sensitivity: float) -> None:
        """Initialize with keywords and sensitivity."""
        self._keywords = keywords
        self._sensitivity = sensitivity
        self._chunk_count = 0
        self._initialized = True

    def process(self, audio: AudioChunk) -> WakeWordResult:
        """Process audio chunk, returning scheduled detection if any."""
        self._chunk_count += 1
        chunk_index = self._chunk_count - 1  # 0-based index

        if chunk_index in self._scheduled_detections:
            confidence = self._scheduled_detections[chunk_index]
            keyword = self._keywords[0] if self._keywords else "ara"
            return WakeWordResult(
                detected=True,
                confidence=confidence,
                keyword=keyword,
                timestamp_ms=audio.timestamp_ms,
            )

        return WakeWordResult(
            detected=False,
            confidence=0.0,
            keyword="",
            timestamp_ms=audio.timestamp_ms,
        )

    def cleanup(self) -> None:
        """Cleanup resources."""
        self._initialized = False
        self._chunk_count = 0
        self._scheduled_detections.clear()

    def schedule_detection(self, at_chunk: int, confidence: float = 0.9) -> None:
        """Schedule a detection at a specific chunk number.

        Args:
            at_chunk: Chunk number (0-based) when detection should occur
            confidence: Confidence level for the detection
        """
        self._scheduled_detections[at_chunk] = confidence

    @property
    def keywords(self) -> list[str]:
        """Get configured keywords."""
        return self._keywords

    @property
    def sensitivity(self) -> float:
        """Get configured sensitivity."""
        return self._sensitivity

    @property
    def chunk_count(self) -> int:
        """Get number of chunks processed."""
        return self._chunk_count


__all__ = ["MockWakeWordDetector"]
