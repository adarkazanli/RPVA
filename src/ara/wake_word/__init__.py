"""Wake word detection module for Ara Voice Assistant.

Provides wake word detection using Porcupine or mock implementation.
"""

from typing import TYPE_CHECKING

from .detector import WakeWordDetector, WakeWordResult
from .mock import MockWakeWordDetector

if TYPE_CHECKING:
    from ..config import WakeWordConfig


def create_wake_word_detector(
    config: "WakeWordConfig | None" = None,
    use_mock: bool = False,
    access_key: str | None = None,
) -> WakeWordDetector:
    """Create a wake word detector instance.

    Args:
        config: Wake word configuration (keyword, sensitivity, model_path)
        use_mock: If True, return mock implementation for testing
        access_key: Picovoice access key (for Porcupine)

    Returns:
        WakeWordDetector implementation configured with the provided config
    """
    if use_mock:
        return MockWakeWordDetector(config=config)

    # Try to use Porcupine
    try:
        from .porcupine import PorcupineWakeWordDetector

        return PorcupineWakeWordDetector(config=config, access_key=access_key)
    except RuntimeError:
        # Fall back to mock if Porcupine not available
        import logging

        logging.getLogger(__name__).warning(
            "Porcupine not available, using mock wake word detector"
        )
        return MockWakeWordDetector(config=config)


__all__ = [
    "MockWakeWordDetector",
    "WakeWordDetector",
    "WakeWordResult",
    "create_wake_word_detector",
]
