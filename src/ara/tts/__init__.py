"""Text-to-speech module for Ara Voice Assistant.

Provides platform-adaptive speech synthesis with optional emotional TTS:
- ElevenLabs: High-quality emotional TTS (if API key configured)
- macOS: Native TTS with "Samantha" voice
- Raspberry Pi: Piper TTS with neural voice
- Other: Falls back to Mock synthesizer
"""

import logging
from typing import TYPE_CHECKING

from .mock import MockSynthesizer
from .platform import Platform, detect_platform
from .synthesizer import SynthesisResult, Synthesizer

if TYPE_CHECKING:
    from ..config import TTSConfig

logger = logging.getLogger(__name__)


def create_synthesizer(
    config: "TTSConfig | None" = None,
    use_mock: bool = False,
    use_elevenlabs: bool | None = None,
) -> Synthesizer:
    """Create the appropriate synthesizer for the current platform.

    Automatically detects the platform and selects the optimal TTS engine:
    - ElevenLabs: If API key configured and use_elevenlabs is True/None
    - macOS: MacOSSynthesizer with "Samantha" voice
    - Raspberry Pi: PiperSynthesizer with neural voice
    - Other: PiperSynthesizer or MockSynthesizer fallback

    Args:
        config: TTS configuration (optional)
        use_mock: If True, force mock synthesizer for testing
        use_elevenlabs: If True, prefer ElevenLabs; if False, skip it;
                       if None (default), use if available

    Returns:
        Synthesizer implementation appropriate for the platform.
        Never returns None - always falls back to MockSynthesizer.
    """
    if use_mock:
        logger.info("TTS: Using MockSynthesizer (requested)")
        return MockSynthesizer()

    platform = detect_platform()
    logger.debug(f"TTS: Detected platform: {platform.name}")

    # Default config values
    voice = "en_US-lessac-medium"
    speed = 1.0

    if config is not None:
        voice = config.voice
        speed = config.speed

    # Try ElevenLabs first if not explicitly disabled
    if use_elevenlabs is not False:
        try:
            from .elevenlabs import ELEVENLABS_AVAILABLE, ElevenLabsSynthesizer

            if ELEVENLABS_AVAILABLE:
                synth = ElevenLabsSynthesizer()
                if synth.is_available:
                    logger.info("TTS: Using ElevenLabsSynthesizer (emotional TTS)")
                    return synth
                elif use_elevenlabs is True:
                    logger.warning("TTS: ElevenLabs requested but not available")
        except Exception as e:
            logger.warning(f"TTS: ElevenLabsSynthesizer failed to initialize: {e}")
            if use_elevenlabs is True:
                raise

    # Platform-specific selection
    if platform == Platform.MACOS:
        # Try macOS native TTS first
        try:
            from .macos import MacOSSynthesizer

            synth = MacOSSynthesizer(voice="Samantha", speed=speed)
            if synth.is_available:
                logger.info("TTS: Using MacOSSynthesizer (native macOS TTS)")
                return synth
            else:
                logger.warning("TTS: macOS say command not available")
        except Exception as e:
            logger.warning(f"TTS: MacOSSynthesizer failed to initialize: {e}")

        # Fall back to Piper on macOS
        try:
            from .piper import PiperSynthesizer

            synth = PiperSynthesizer(voice=voice, speed=speed)
            if synth.is_available:
                logger.info("TTS: Using PiperSynthesizer (fallback on macOS)")
                return synth
        except Exception:
            pass

    elif platform == Platform.RASPBERRY_PI:
        # Use Piper on Raspberry Pi
        try:
            from .piper import PiperSynthesizer

            synth = PiperSynthesizer(voice=voice, speed=speed)
            if synth.is_available:
                logger.info("TTS: Using PiperSynthesizer (Raspberry Pi)")
                return synth
            else:
                logger.warning("TTS: Piper models not available on Raspberry Pi")
        except Exception as e:
            logger.warning(f"TTS: PiperSynthesizer failed to initialize: {e}")

    else:
        # Other platforms - try Piper
        try:
            from .piper import PiperSynthesizer

            synth = PiperSynthesizer(voice=voice, speed=speed)
            if synth.is_available:
                logger.info("TTS: Using PiperSynthesizer (other platform)")
                return synth
        except Exception:
            pass

    # Final fallback - MockSynthesizer is always available
    logger.warning("TTS: Using MockSynthesizer (fallback)")
    return MockSynthesizer()


__all__ = [
    "MockSynthesizer",
    "Platform",
    "Synthesizer",
    "SynthesisResult",
    "create_synthesizer",
    "detect_platform",
]
