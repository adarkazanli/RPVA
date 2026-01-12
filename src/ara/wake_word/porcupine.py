"""Porcupine wake word detector implementation.

Uses Picovoice's Porcupine for efficient, low-latency wake word detection.
Supports custom wake words with Porcupine's built-in keywords.
"""

import logging
import os
from typing import TYPE_CHECKING

from .detector import WakeWordResult

if TYPE_CHECKING:
    from ..audio.capture import AudioChunk

# Porcupine import with fallback
try:
    import pvporcupine

    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    pvporcupine = None  # type: ignore

logger = logging.getLogger(__name__)


class PorcupineWakeWordDetector:
    """Wake word detector using Picovoice Porcupine.

    Porcupine provides efficient on-device wake word detection optimized
    for edge devices like Raspberry Pi.
    """

    def __init__(self, access_key: str | None = None) -> None:
        """Initialize Porcupine detector.

        Args:
            access_key: Picovoice access key. If not provided, will look for
                       PICOVOICE_ACCESS_KEY environment variable.

        Raises:
            RuntimeError: If Porcupine is not available
        """
        if not PORCUPINE_AVAILABLE:
            raise RuntimeError(
                "Porcupine not available. Install with: pip install pvporcupine"
            )

        self._access_key = access_key or os.environ.get("PICOVOICE_ACCESS_KEY")
        self._porcupine = None
        self._keywords: list[str] = []
        self._sensitivity: float = 0.5

    def initialize(self, keywords: list[str], sensitivity: float) -> None:
        """Initialize Porcupine with keywords.

        Args:
            keywords: List of wake words. Can be built-in keywords like
                     "porcupine", "bumblebee", "alexa", etc.
            sensitivity: Detection sensitivity (0.0 to 1.0)
        """
        if not self._access_key:
            raise RuntimeError(
                "Porcupine access key required. Set PICOVOICE_ACCESS_KEY env var "
                "or pass access_key to constructor. Get a free key at "
                "https://console.picovoice.ai/"
            )

        self._keywords = keywords
        self._sensitivity = sensitivity

        # Map common keywords to Porcupine built-in keywords
        # Note: "ara" is not a built-in keyword, would need custom training
        porcupine_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            # Check if it's a built-in keyword
            if kw_lower in pvporcupine.KEYWORDS:
                porcupine_keywords.append(kw_lower)
            else:
                # For custom keywords, we'd need a .ppn file
                logger.warning(
                    f"Keyword '{kw}' is not a built-in Porcupine keyword. "
                    "Using 'porcupine' as fallback. For custom keywords, "
                    "train a model at https://console.picovoice.ai/"
                )
                porcupine_keywords.append("porcupine")

        sensitivities = [sensitivity] * len(porcupine_keywords)

        self._porcupine = pvporcupine.create(
            access_key=self._access_key,
            keywords=porcupine_keywords,
            sensitivities=sensitivities,
        )

        logger.info(
            f"Porcupine initialized with keywords: {porcupine_keywords}, "
            f"sensitivity: {sensitivity}"
        )

    def process(self, audio: "AudioChunk") -> WakeWordResult:
        """Process audio chunk for wake word detection.

        Args:
            audio: Audio chunk (must be 16kHz, 16-bit, mono)

        Returns:
            WakeWordResult with detection status
        """
        if self._porcupine is None:
            raise RuntimeError("Detector not initialized. Call initialize() first.")

        # Porcupine expects specific frame length
        frame_length = self._porcupine.frame_length

        # Convert bytes to int16 array
        import struct

        num_samples = len(audio.data) // 2
        pcm = struct.unpack(f"{num_samples}h", audio.data)

        # Process in frames
        for i in range(0, len(pcm) - frame_length + 1, frame_length):
            frame = pcm[i : i + frame_length]
            keyword_index = self._porcupine.process(frame)

            if keyword_index >= 0:
                keyword = self._keywords[keyword_index] if self._keywords else "unknown"
                logger.info(f"Wake word detected: {keyword}")
                return WakeWordResult(
                    detected=True,
                    confidence=self._sensitivity,  # Porcupine doesn't provide confidence
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
        """Release Porcupine resources."""
        if self._porcupine is not None:
            self._porcupine.delete()
            self._porcupine = None
            logger.info("Porcupine resources released")

    @property
    def frame_length(self) -> int:
        """Get required frame length for processing."""
        if self._porcupine is None:
            return 512  # Default Porcupine frame length
        return self._porcupine.frame_length

    @property
    def sample_rate(self) -> int:
        """Get required sample rate."""
        if self._porcupine is None:
            return 16000  # Porcupine requires 16kHz
        return self._porcupine.sample_rate


__all__ = ["PorcupineWakeWordDetector"]
