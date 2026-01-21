"""Contract definitions for Platform-Adaptive TTS module.

These contracts define the expected behavior and interfaces for the TTS system.
Tests should verify implementations against these contracts.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol


class Platform(Enum):
    """Detected platform for TTS engine selection."""

    MACOS = auto()
    RASPBERRY_PI = auto()
    OTHER = auto()


@dataclass
class SynthesisResult:
    """Result of text-to-speech synthesis.

    Contract:
    - audio: Non-empty bytes of 16-bit PCM audio data
    - sample_rate: Positive integer (typically 22050 or 24000)
    - duration_ms: Positive integer representing audio duration
    - latency_ms: Non-negative integer representing synthesis time
    """

    audio: bytes
    sample_rate: int
    duration_ms: int
    latency_ms: int

    def __post_init__(self) -> None:
        """Validate contract invariants."""
        assert len(self.audio) > 0, "audio must not be empty"
        assert self.sample_rate > 0, "sample_rate must be positive"
        assert self.duration_ms > 0, "duration_ms must be positive"
        assert self.latency_ms >= 0, "latency_ms must be non-negative"


class Synthesizer(Protocol):
    """Protocol defining the TTS synthesizer interface.

    Contract:
    - All implementations MUST be thread-safe for synthesize()
    - synthesize() MUST return valid SynthesisResult or raise RuntimeError
    - is_available MUST be checked before using the synthesizer
    """

    @property
    def is_available(self) -> bool:
        """Check if the synthesizer is ready to use.

        Contract:
        - MUST return True only if synthesize() will succeed
        - MUST NOT raise exceptions
        """
        ...

    def synthesize(self, text: str) -> SynthesisResult:
        """Convert text to speech audio.

        Contract:
        - MUST accept any non-empty string
        - MUST return SynthesisResult with valid audio data
        - MUST complete within 500ms for typical phrases (< 50 words)
        - SHOULD handle empty string gracefully (return minimal audio or raise)

        Args:
            text: Text to synthesize (non-empty)

        Returns:
            SynthesisResult with PCM audio data

        Raises:
            RuntimeError: If synthesis fails
        """
        ...

    def set_voice(self, voice_id: str) -> None:
        """Set the voice for synthesis.

        Contract:
        - MUST accept valid voice ID for the platform
        - SHOULD raise ValueError for invalid voice ID
        - Changes take effect on next synthesize() call

        Args:
            voice_id: Platform-specific voice identifier
        """
        ...

    def set_speed(self, speed: float) -> None:
        """Set speech speed multiplier.

        Contract:
        - MUST accept values between 0.5 and 2.0
        - SHOULD clamp values outside this range
        - 1.0 represents normal speed

        Args:
            speed: Speed multiplier (0.5 = half speed, 2.0 = double speed)
        """
        ...

    def get_available_voices(self) -> list[str]:
        """List available voice identifiers.

        Contract:
        - MUST return list (may be empty if no voices available)
        - MUST NOT raise exceptions

        Returns:
            List of voice IDs available on this platform
        """
        ...


# Platform detection contract
def detect_platform() -> Platform:
    """Detect the current platform for TTS engine selection.

    Contract:
    - MUST return a valid Platform enum value
    - MUST NOT raise exceptions
    - MUST return MACOS for Darwin systems
    - MUST return RASPBERRY_PI for Linux on ARM
    - MUST return OTHER for all other platforms

    Returns:
        Platform enum indicating the detected platform
    """
    ...


# Factory function contract
def create_synthesizer(
    config: object | None = None,
    use_mock: bool = False,
) -> Synthesizer:
    """Create the appropriate synthesizer for the current platform.

    Contract:
    - If use_mock=True, MUST return MockSynthesizer
    - If platform=MACOS, SHOULD return MacOSSynthesizer (fallback to Piper/Mock)
    - If platform=RASPBERRY_PI, SHOULD return PiperSynthesizer (fallback to Mock)
    - MUST never return None
    - MUST never raise exceptions (always fall back to Mock)
    - MUST log which synthesizer was selected

    Args:
        config: Optional TTS configuration
        use_mock: If True, force mock synthesizer

    Returns:
        Synthesizer implementation appropriate for the platform
    """
    ...
