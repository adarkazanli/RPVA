"""Speech-to-text module for Ara Voice Assistant.

Provides transcription using faster-whisper or mock implementation.
"""

from typing import TYPE_CHECKING

from .mock import MockTranscriber
from .transcriber import PartialTranscription, TranscriptionResult, Transcriber

if TYPE_CHECKING:
    from ..config import STTConfig


def create_transcriber(
    config: "STTConfig | None" = None,
    use_mock: bool = False,
) -> Transcriber:
    """Create a transcriber instance.

    Args:
        config: STT configuration
        use_mock: If True, return mock implementation for testing

    Returns:
        Transcriber implementation
    """
    if use_mock:
        return MockTranscriber()

    # Default config values
    model_size = "base.en"
    device = "cpu"
    compute_type = "int8"

    if config is not None:
        model_size = config.model
        device = config.device
        compute_type = config.compute_type

    # Try to use faster-whisper
    try:
        from .whisper import WhisperTranscriber

        return WhisperTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
        )
    except RuntimeError:
        # Fall back to mock if faster-whisper not available
        import logging

        logging.getLogger(__name__).warning(
            "faster-whisper not available, using mock transcriber"
        )
        return MockTranscriber()


__all__ = [
    "MockTranscriber",
    "PartialTranscription",
    "TranscriptionResult",
    "Transcriber",
    "create_transcriber",
]
