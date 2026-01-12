"""Mock synthesizer for testing.

Provides a controllable mock implementation for unit and integration testing.
"""

import math
import struct
import time

from .synthesizer import SynthesisResult


class MockSynthesizer:
    """Mock synthesizer for testing.

    Generates simple tones instead of actual speech for testing purposes.
    """

    def __init__(self, sample_rate: int = 22050) -> None:
        """Initialize mock synthesizer.

        Args:
            sample_rate: Output sample rate
        """
        self._sample_rate = sample_rate
        self._voice: str = "en_US-mock-medium"
        self._speed: float = 1.0
        self._call_count: int = 0
        self._synthesized_texts: list[str] = []
        self._latency_ms: int = 50

    def synthesize(self, text: str) -> SynthesisResult:
        """Synthesize text to audio (generates tone).

        The tone duration is proportional to text length.
        """
        self._call_count += 1
        self._synthesized_texts.append(text)

        start_time = time.time()

        # Estimate duration based on text length
        # Roughly 100ms per word at normal speed
        words = len(text.split())
        base_duration_ms = max(100, words * 100)
        duration_ms = int(base_duration_ms / self._speed)

        # Generate simple tone
        audio = self._generate_tone(440, duration_ms)

        # Simulate latency
        time.sleep(self._latency_ms / 1000)
        latency_ms = int((time.time() - start_time) * 1000)

        return SynthesisResult(
            audio=audio,
            sample_rate=self._sample_rate,
            duration_ms=duration_ms,
            latency_ms=latency_ms,
        )

    def _generate_tone(self, frequency: int, duration_ms: int) -> bytes:
        """Generate a simple sine wave tone."""
        num_samples = int(self._sample_rate * duration_ms / 1000)
        audio_data = []

        for i in range(num_samples):
            t = i / self._sample_rate

            # Apply envelope
            envelope = 1.0
            attack = int(self._sample_rate * 0.01)
            release = int(self._sample_rate * 0.01)

            if i < attack:
                envelope = i / attack
            elif i > num_samples - release:
                envelope = (num_samples - i) / release

            sample = int(32767 * 0.3 * envelope * math.sin(2 * math.pi * frequency * t))
            audio_data.append(struct.pack("<h", sample))

        return b"".join(audio_data)

    def set_voice(self, voice_id: str) -> None:
        """Set voice."""
        self._voice = voice_id

    def set_speed(self, speed: float) -> None:
        """Set speech speed."""
        self._speed = max(0.5, min(2.0, speed))

    def get_available_voices(self) -> list[str]:
        """Return mock available voices."""
        return [
            "en_US-mock-medium",
            "en_US-mock-high",
            "en_GB-mock-medium",
        ]

    def set_latency(self, latency_ms: int) -> None:
        """Set simulated latency."""
        self._latency_ms = latency_ms

    @property
    def voice(self) -> str:
        """Get current voice."""
        return self._voice

    @property
    def speed(self) -> float:
        """Get current speed."""
        return self._speed

    @property
    def call_count(self) -> int:
        """Get number of synthesize calls."""
        return self._call_count

    @property
    def synthesized_texts(self) -> list[str]:
        """Get list of synthesized texts."""
        return self._synthesized_texts.copy()

    def clear(self) -> None:
        """Reset mock state."""
        self._call_count = 0
        self._synthesized_texts.clear()


__all__ = ["MockSynthesizer"]
