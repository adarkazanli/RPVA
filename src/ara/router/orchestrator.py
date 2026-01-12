"""Voice loop orchestrator.

Coordinates the full voice interaction pipeline:
Wake Word → STT → LLM → TTS → Playback
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..audio.capture import AudioCapture
    from ..audio.playback import AudioPlayback
    from ..config import AraConfig
    from ..feedback import AudioFeedback
    from ..llm.model import LanguageModel
    from ..stt.transcriber import Transcriber
    from ..tts.synthesizer import Synthesizer
    from ..wake_word.detector import WakeWordDetector

from ..feedback import FeedbackType

logger = logging.getLogger(__name__)


@dataclass
class InteractionResult:
    """Result of a voice interaction.

    Attributes:
        transcript: User's spoken text
        response_text: Assistant's response
        latency_breakdown: Per-component latencies in ms
        total_latency_ms: Total end-to-end latency
        error: Error message if interaction failed
    """

    transcript: str
    response_text: str
    latency_breakdown: dict[str, int] = field(default_factory=dict)
    total_latency_ms: int = 0
    error: str | None = None


class Orchestrator:
    """Main voice loop orchestrator.

    Coordinates the complete voice interaction pipeline:
    1. Listen for wake word
    2. Capture user speech
    3. Transcribe to text (STT)
    4. Generate response (LLM)
    5. Synthesize speech (TTS)
    6. Play response audio
    """

    def __init__(
        self,
        audio_capture: "AudioCapture",
        audio_playback: "AudioPlayback",
        wake_word_detector: "WakeWordDetector",
        transcriber: "Transcriber",
        language_model: "LanguageModel",
        synthesizer: "Synthesizer",
        feedback: "AudioFeedback",
    ) -> None:
        """Initialize orchestrator with components.

        Args:
            audio_capture: Audio input capture
            audio_playback: Audio output playback
            wake_word_detector: Wake word detection
            transcriber: Speech-to-text
            language_model: LLM for response generation
            synthesizer: Text-to-speech
            feedback: Audio feedback sounds
        """
        self._capture = audio_capture
        self._playback = audio_playback
        self._wake_word = wake_word_detector
        self._transcriber = transcriber
        self._llm = language_model
        self._synthesizer = synthesizer
        self._feedback = feedback

        self._running = False
        self._thread: threading.Thread | None = None
        self._ready = False

        # Configuration
        self._silence_timeout_ms = 2000  # Stop recording after 2s silence
        self._max_recording_ms = 10000  # Max 10s recording

    @classmethod
    def from_config(
        cls,
        config: "AraConfig",
        use_mocks: bool = False,
    ) -> "Orchestrator":
        """Create orchestrator from configuration.

        Args:
            config: Ara configuration
            use_mocks: Use mock implementations for testing

        Returns:
            Configured Orchestrator instance
        """
        from ..audio import create_audio_capture, create_audio_playback
        from ..feedback.audio import MockFeedback, SoundFeedback
        from ..llm import create_language_model
        from ..stt import create_transcriber
        from ..tts import create_synthesizer
        from ..wake_word import create_wake_word_detector

        # Create components
        audio_capture = create_audio_capture(config.audio, use_mock=use_mocks)
        audio_playback = create_audio_playback(config.audio, use_mock=use_mocks)
        wake_word = create_wake_word_detector(config.wake_word, use_mock=use_mocks)
        transcriber = create_transcriber(config.stt, use_mock=use_mocks)
        llm = create_language_model(config.llm, use_mock=use_mocks)
        synthesizer = create_synthesizer(config.tts, use_mock=use_mocks)

        if use_mocks:
            feedback: "AudioFeedback" = MockFeedback()
        else:
            feedback = SoundFeedback(audio_playback, config.feedback)

        # Initialize wake word detector
        wake_word.initialize(
            keywords=[config.wake_word.keyword],
            sensitivity=config.wake_word.sensitivity,
        )

        orch = cls(
            audio_capture=audio_capture,
            audio_playback=audio_playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )

        orch._ready = True
        return orch

    def process_single_interaction(self) -> InteractionResult | None:
        """Process a single voice interaction.

        Waits for wake word, records speech, and generates response.

        Returns:
            InteractionResult or None if interaction failed
        """
        latencies: dict[str, int] = {}
        start_time = time.time()

        try:
            # Step 1: Wait for wake word
            logger.debug("Listening for wake word...")
            wake_result = self._wait_for_wake_word()

            if not wake_result:
                return None

            latencies["wake_ms"] = int((time.time() - start_time) * 1000)

            # Play wake feedback
            self._feedback.play(FeedbackType.WAKE_WORD_DETECTED)
            logger.info("Wake word detected, listening for speech...")

            # Step 2: Record user speech
            stt_start = time.time()
            audio_data = self._record_speech()

            if not audio_data:
                logger.warning("No speech detected")
                return None

            # Step 3: Transcribe speech
            transcript_result = self._transcriber.transcribe(audio_data, 16000)
            transcript = transcript_result.text.strip()

            if not transcript:
                logger.warning("Empty transcription")
                return None

            latencies["stt_ms"] = int((time.time() - stt_start) * 1000)
            logger.info(f"Transcribed: '{transcript}'")

            # Step 4: Generate LLM response
            llm_start = time.time()
            llm_response = self._llm.generate(transcript)
            response_text = llm_response.text.strip()
            latencies["llm_ms"] = int((time.time() - llm_start) * 1000)
            logger.info(f"LLM response: '{response_text[:50]}...'")

            # Step 5: Synthesize speech
            tts_start = time.time()
            synthesis_result = self._synthesizer.synthesize(response_text)
            latencies["tts_ms"] = int((time.time() - tts_start) * 1000)

            # Step 6: Play response
            play_start = time.time()
            self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            latencies["play_ms"] = int((time.time() - play_start) * 1000)

            total_latency = int((time.time() - start_time) * 1000)

            logger.info(
                f"Interaction complete: {total_latency}ms total "
                f"(STT:{latencies['stt_ms']}ms, LLM:{latencies['llm_ms']}ms, "
                f"TTS:{latencies['tts_ms']}ms)"
            )

            return InteractionResult(
                transcript=transcript,
                response_text=response_text,
                latency_breakdown=latencies,
                total_latency_ms=total_latency,
            )

        except Exception as e:
            logger.error(f"Interaction failed: {e}")
            self._feedback.play(FeedbackType.ERROR)
            return InteractionResult(
                transcript="",
                response_text="",
                error=str(e),
            )

    def _wait_for_wake_word(self) -> bool:
        """Wait for wake word detection.

        Returns:
            True if wake word detected
        """
        self._capture.start()

        try:
            for chunk in self._capture.stream():
                result = self._wake_word.process(chunk)
                if result.detected:
                    return True

                # Check if we should stop
                if not self._running:
                    return False

        finally:
            self._capture.stop()

        return False

    def _record_speech(self) -> bytes:
        """Record user speech until silence detected.

        Returns:
            Recorded audio bytes
        """
        audio_buffer = b""
        silence_start: float | None = None
        recording_start = time.time()

        self._capture.start()

        try:
            for chunk in self._capture.stream():
                audio_buffer += chunk.data

                # Check for silence (simple energy-based detection)
                energy = self._calculate_energy(chunk.data)
                is_silence = energy < 500  # Threshold

                if is_silence:
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) * 1000 > self._silence_timeout_ms:
                        # Silence timeout reached
                        logger.debug("Silence detected, stopping recording")
                        break
                else:
                    silence_start = None

                # Check max recording time
                if (time.time() - recording_start) * 1000 > self._max_recording_ms:
                    logger.debug("Max recording time reached")
                    break

        finally:
            self._capture.stop()

        return audio_buffer

    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calculate audio energy for silence detection."""
        import struct

        if len(audio_data) < 2:
            return 0.0

        # Convert to int16 samples
        num_samples = len(audio_data) // 2
        samples = struct.unpack(f"{num_samples}h", audio_data)

        # Calculate RMS energy
        sum_squares = sum(s * s for s in samples)
        rms = (sum_squares / num_samples) ** 0.5

        return rms

    def start(self) -> None:
        """Start the voice loop in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Voice loop started")

    def stop(self) -> None:
        """Stop the voice loop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Voice loop stopped")

    def _run_loop(self) -> None:
        """Main voice loop."""
        while self._running:
            try:
                result = self.process_single_interaction()
                if result and result.error:
                    logger.error(f"Interaction error: {result.error}")
            except Exception as e:
                logger.error(f"Voice loop error: {e}")
                time.sleep(1)  # Brief pause before retry

    @property
    def is_ready(self) -> bool:
        """Check if orchestrator is ready."""
        return self._ready

    @property
    def is_running(self) -> bool:
        """Check if voice loop is running."""
        return self._running


__all__ = ["InteractionResult", "Orchestrator"]
