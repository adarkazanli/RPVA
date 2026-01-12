"""Wake word detector protocol and data classes.

Defines the interface for wake word detection that all implementations
must follow.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..audio.capture import AudioChunk


@dataclass
class WakeWordResult:
    """Result of wake word detection.

    Attributes:
        detected: True if wake word was detected
        confidence: Detection confidence (0.0 to 1.0)
        keyword: The wake word that was detected (empty if not detected)
        timestamp_ms: Timestamp when detection occurred
    """

    detected: bool
    confidence: float
    keyword: str
    timestamp_ms: int


class WakeWordDetector(Protocol):
    """Interface for wake word detection.

    Implementations listen for specific keywords in audio streams
    and signal when they are detected.
    """

    def initialize(self, keywords: list[str], sensitivity: float) -> None:
        """Initialize detector with keywords and sensitivity.

        Args:
            keywords: List of wake words to listen for
            sensitivity: Detection sensitivity (0.0 to 1.0)
                        Higher values = more sensitive but more false positives

        Raises:
            RuntimeError: If initialization fails
        """
        ...

    def process(self, audio: "AudioChunk") -> WakeWordResult:
        """Process audio chunk for wake word detection.

        Args:
            audio: Audio chunk to process

        Returns:
            WakeWordResult indicating if wake word was detected
        """
        ...

    def cleanup(self) -> None:
        """Release resources.

        Should be called when detector is no longer needed.
        """
        ...


__all__ = ["WakeWordDetector", "WakeWordResult"]
