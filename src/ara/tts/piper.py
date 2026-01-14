"""Piper TTS synthesizer implementation.

Uses Piper for fast, high-quality text-to-speech on CPU.
"""

import logging
import time
from pathlib import Path
from typing import Any

from .synthesizer import SynthesisResult

logger = logging.getLogger(__name__)

# Check for piper availability
PIPER_AVAILABLE = False
try:
    # Try importing piper-tts
    import piper

    PIPER_AVAILABLE = True
except ImportError:
    pass


class PiperSynthesizer:
    """Text-to-speech synthesizer using Piper.

    Piper provides fast, high-quality TTS that runs efficiently on CPU,
    making it ideal for Raspberry Pi deployment.
    """

    def __init__(
        self,
        voice: str = "en_US-lessac-medium",
        speed: float = 1.0,
        models_dir: Path | None = None,
    ) -> None:
        """Initialize Piper synthesizer.

        Args:
            voice: Voice identifier (e.g., "en_US-lessac-medium")
            speed: Speech speed multiplier
            models_dir: Directory containing Piper voice models

        Raises:
            RuntimeError: If Piper is not available
        """
        self._voice = voice
        self._speed = speed
        self._models_dir = models_dir or Path("models/piper")
        self._piper: Any = None

        # Try to initialize Piper
        self._init_piper()

    def _init_piper(self) -> None:
        """Initialize Piper voice."""
        if not PIPER_AVAILABLE:
            logger.warning("piper-tts not available. Install with: pip install piper-tts")
            return

        model_path = self._models_dir / f"{self._voice}.onnx"
        config_path = self._models_dir / f"{self._voice}.onnx.json"

        if not model_path.exists():
            logger.warning(
                f"Piper model not found: {model_path}. Run scripts/download_models.sh to download."
            )
            return

        try:
            self._piper = piper.PiperVoice.load(str(model_path), str(config_path))
            logger.info(f"Piper initialized with voice: {self._voice}")
        except Exception as e:
            logger.error(f"Failed to load Piper voice: {e}")
            self._piper = None

    def synthesize(self, text: str) -> SynthesisResult:
        """Synthesize text to speech.

        Args:
            text: Text to synthesize

        Returns:
            SynthesisResult with audio data
        """
        start_time = time.time()

        if self._piper is None:
            # Fall back to simple tone generation
            return self._fallback_synthesize(text)

        try:
            # Synthesize with Piper
            audio_data = b""
            sample_rate = self._piper.config.sample_rate

            # Piper synthesize yields AudioChunk objects
            for chunk in self._piper.synthesize(text):
                audio_data += chunk.audio_int16_bytes

            # Apply speed adjustment if needed
            if self._speed != 1.0:
                audio_data = self._adjust_speed(audio_data, sample_rate)

            duration_ms = int(len(audio_data) / (sample_rate * 2) * 1000)
            latency_ms = int((time.time() - start_time) * 1000)

            logger.debug(f"Synthesized '{text[:30]}...' in {latency_ms}ms ({duration_ms}ms audio)")

            return SynthesisResult(
                audio=audio_data,
                sample_rate=sample_rate,
                duration_ms=duration_ms,
                latency_ms=latency_ms,
            )

        except Exception as e:
            logger.error(f"Piper synthesis failed: {e}")
            return self._fallback_synthesize(text)

    def _fallback_synthesize(self, text: str) -> SynthesisResult:
        """Fallback synthesis using simple tone."""
        import math
        import struct

        sample_rate = 22050
        words = len(text.split())
        duration_ms = max(200, words * 100)

        # Generate simple tone
        num_samples = int(sample_rate * duration_ms / 1000)
        audio_data = []

        for i in range(num_samples):
            t = i / sample_rate
            envelope = 1.0
            if i < sample_rate * 0.01:
                envelope = i / (sample_rate * 0.01)
            elif i > num_samples - sample_rate * 0.01:
                envelope = (num_samples - i) / (sample_rate * 0.01)

            sample = int(32767 * 0.3 * envelope * math.sin(2 * math.pi * 440 * t))
            audio_data.append(struct.pack("<h", sample))

        return SynthesisResult(
            audio=b"".join(audio_data),
            sample_rate=sample_rate,
            duration_ms=duration_ms,
            latency_ms=0,
        )

    def _adjust_speed(self, audio: bytes, sample_rate: int) -> bytes:  # noqa: ARG002
        """Adjust audio playback speed.

        Simple resampling - for production, use a proper audio library.
        """
        import numpy as np

        # Convert to numpy array
        audio_array = np.frombuffer(audio, dtype=np.int16)

        # Resample for speed adjustment
        new_length = int(len(audio_array) / self._speed)
        indices = np.linspace(0, len(audio_array) - 1, new_length).astype(int)
        resampled = audio_array[indices]

        return resampled.tobytes()

    def set_voice(self, voice_id: str) -> None:
        """Set voice and reload model."""
        self._voice = voice_id
        self._init_piper()

    def set_speed(self, speed: float) -> None:
        """Set speech speed."""
        self._speed = max(0.5, min(2.0, speed))

    def get_available_voices(self) -> list[str]:
        """Return list of available voices."""
        if not self._models_dir.exists():
            return []

        voices = []
        for model_file in self._models_dir.glob("*.onnx"):
            if not model_file.name.endswith(".onnx.json"):
                voice_name = model_file.stem
                voices.append(voice_name)

        return voices

    @property
    def voice(self) -> str:
        """Get current voice."""
        return self._voice

    @property
    def is_available(self) -> bool:
        """Check if Piper is available."""
        return self._piper is not None


__all__ = ["PiperSynthesizer"]
