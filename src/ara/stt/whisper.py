"""Faster-whisper transcriber implementation.

Uses faster-whisper (CTranslate2) for efficient speech-to-text on CPU/GPU.
"""

import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .transcriber import PartialTranscription, TranscriptionResult

# faster-whisper import with fallback
try:
    from faster_whisper import WhisperModel

    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False
    WhisperModel = None  # type: ignore

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Speech-to-text transcriber using faster-whisper.

    Faster-whisper provides efficient Whisper inference using CTranslate2,
    with support for CPU int8 quantization and GPU acceleration.
    """

    def __init__(
        self,
        model_size: str = "base.en",
        device: str = "cpu",
        compute_type: str = "int8",
        model_path: Path | None = None,
    ) -> None:
        """Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size (tiny.en, base.en, small.en, etc.)
            device: Device to run on ("cpu", "cuda", "auto")
            compute_type: Computation type ("float16", "int8", "float32")
            model_path: Optional path to pre-downloaded model

        Raises:
            RuntimeError: If faster-whisper is not available
        """
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper not available. Install with: pip install faster-whisper"
            )

        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model_path = model_path
        self._model: Any = None
        self._language: str = "en"

    def _ensure_model_loaded(self) -> None:
        """Load model if not already loaded."""
        if self._model is not None:
            return

        logger.info(
            f"Loading Whisper model: {self._model_size} "
            f"(device={self._device}, compute={self._compute_type})"
        )

        start = time.time()

        if self._model_path and self._model_path.exists():
            self._model = WhisperModel(
                str(self._model_path),
                device=self._device,
                compute_type=self._compute_type,
            )
        else:
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )

        load_time = (time.time() - start) * 1000
        logger.info(f"Whisper model loaded in {load_time:.0f}ms")

    def transcribe(self, audio: bytes, sample_rate: int) -> TranscriptionResult:
        """Transcribe audio to text.

        Args:
            audio: Raw PCM audio bytes (16-bit, mono)
            sample_rate: Audio sample rate (should be 16000 for Whisper)

        Returns:
            TranscriptionResult with transcribed text
        """
        self._ensure_model_loaded()

        start_time = time.time()

        # Convert bytes to numpy array
        import numpy as np

        audio_array = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0

        # Resample if needed (Whisper expects 16kHz)
        if sample_rate != 16000:
            # Simple resampling - for production, use librosa or scipy
            ratio = 16000 / sample_rate
            new_length = int(len(audio_array) * ratio)
            indices = np.linspace(0, len(audio_array) - 1, new_length).astype(int)
            audio_array = audio_array[indices]

        # Transcribe
        segments, info = self._model.transcribe(
            audio_array,
            language=self._language if self._language != "auto" else None,
            beam_size=1,  # Fast mode
            vad_filter=True,
        )

        # Collect segments
        text_parts = []
        word_segments = []

        for segment in segments:
            text_parts.append(segment.text.strip())
            if hasattr(segment, "words") and segment.words:
                for word in segment.words:
                    word_segments.append(
                        {
                            "word": word.word,
                            "start": word.start,
                            "end": word.end,
                        }
                    )

        text = " ".join(text_parts).strip()
        duration_ms = int(len(audio) / (sample_rate * 2) * 1000)
        latency_ms = int((time.time() - start_time) * 1000)

        logger.debug(
            f"Transcribed {duration_ms}ms audio in {latency_ms}ms: '{text[:50]}...'"
        )

        return TranscriptionResult(
            text=text,
            confidence=info.language_probability if info else 0.9,
            language=info.language if info else self._language,
            duration_ms=duration_ms,
            segments=word_segments,
        )

    def transcribe_stream(
        self, audio_stream: Iterator[bytes]
    ) -> Iterator[PartialTranscription]:
        """Stream transcription (collects audio then transcribes).

        Note: faster-whisper doesn't support true streaming, so we
        buffer audio and transcribe in chunks.
        """
        self._ensure_model_loaded()

        # Buffer audio chunks
        audio_buffer = b""
        for chunk in audio_stream:
            audio_buffer += chunk

            # Transcribe every ~2 seconds of audio
            if len(audio_buffer) >= 16000 * 2 * 2:  # 2 seconds at 16kHz, 16-bit
                result = self.transcribe(audio_buffer, 16000)
                yield PartialTranscription(text=result.text, is_final=False)
                audio_buffer = b""

        # Final transcription
        if audio_buffer:
            result = self.transcribe(audio_buffer, 16000)
            yield PartialTranscription(text=result.text, is_final=True)

    def set_language(self, language: str) -> None:
        """Set language for transcription."""
        self._language = language

    @property
    def model_size(self) -> str:
        """Get model size."""
        return self._model_size

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model is not None


__all__ = ["WhisperTranscriber"]
