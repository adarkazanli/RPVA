"""Text-to-speech module for Ara Voice Assistant.

Provides speech synthesis using Piper or mock implementation.
"""

from typing import TYPE_CHECKING

from .mock import MockSynthesizer
from .synthesizer import Synthesizer, SynthesisResult

if TYPE_CHECKING:
    from ..config import TTSConfig


def create_synthesizer(
    config: "TTSConfig | None" = None,
    use_mock: bool = False,
) -> Synthesizer:
    """Create a synthesizer instance.

    Args:
        config: TTS configuration
        use_mock: If True, return mock implementation for testing

    Returns:
        Synthesizer implementation
    """
    if use_mock:
        return MockSynthesizer()

    # Default config values
    voice = "en_US-lessac-medium"
    speed = 1.0

    if config is not None:
        voice = config.voice
        speed = config.speed

    # Try to use Piper
    try:
        from .piper import PiperSynthesizer

        synth = PiperSynthesizer(voice=voice, speed=speed)
        if synth.is_available:
            return synth
        else:
            # Piper not available, fall back to mock
            import logging

            logging.getLogger(__name__).warning(
                "Piper models not available, using mock synthesizer"
            )
            return MockSynthesizer()
    except Exception:
        # Fall back to mock
        import logging

        logging.getLogger(__name__).warning(
            "Piper not available, using mock synthesizer"
        )
        return MockSynthesizer()


__all__ = [
    "MockSynthesizer",
    "Synthesizer",
    "SynthesisResult",
    "create_synthesizer",
]
