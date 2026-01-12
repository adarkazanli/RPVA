"""Integration tests for the voice loop orchestrator."""

import pytest

from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
from ara.config import AraConfig
from ara.feedback import FeedbackType
from ara.feedback.audio import MockFeedback
from ara.llm.mock import MockLanguageModel
from ara.router.orchestrator import Orchestrator
from ara.stt.mock import MockTranscriber
from ara.tts.mock import MockSynthesizer
from ara.wake_word.mock import MockWakeWordDetector


class TestVoiceLoopIntegration:
    """Integration tests for complete voice loop."""

    @pytest.fixture
    def mock_components(self) -> dict:
        """Create mock components for testing."""
        return {
            "audio_capture": MockAudioCapture(sample_rate=16000),
            "audio_playback": MockAudioPlayback(sample_rate=22050),
            "wake_word": MockWakeWordDetector(),
            "transcriber": MockTranscriber(),
            "llm": MockLanguageModel(),
            "synthesizer": MockSynthesizer(),
            "feedback": MockFeedback(),
        }

    @pytest.fixture
    def orchestrator(self, mock_components: dict) -> Orchestrator:
        """Create orchestrator with mock components."""
        orch = Orchestrator(
            audio_capture=mock_components["audio_capture"],
            audio_playback=mock_components["audio_playback"],
            wake_word_detector=mock_components["wake_word"],
            transcriber=mock_components["transcriber"],
            language_model=mock_components["llm"],
            synthesizer=mock_components["synthesizer"],
            feedback=mock_components["feedback"],
        )
        return orch

    def test_process_single_interaction(
        self, orchestrator: Orchestrator, mock_components: dict
    ) -> None:
        """Test processing a single voice interaction."""
        # Setup: wake word detected, transcription ready, LLM response ready
        mock_components["wake_word"].schedule_detection(at_chunk=0, confidence=0.9)
        mock_components["transcriber"].set_response("what time is it")
        mock_components["llm"].set_response("It's 3:30 in the afternoon.")

        # Process one interaction
        result = orchestrator.process_single_interaction()

        # Verify the pipeline worked
        assert result is not None
        assert result.transcript == "what time is it"
        assert "3:30" in result.response_text

        # Verify TTS was called
        assert mock_components["synthesizer"].call_count == 1

        # Verify audio was played
        assert mock_components["audio_playback"].play_count >= 1

    def test_wake_word_triggers_feedback(
        self, orchestrator: Orchestrator, mock_components: dict
    ) -> None:
        """Test that wake word detection triggers feedback sound."""
        mock_components["wake_word"].schedule_detection(at_chunk=0, confidence=0.9)
        mock_components["transcriber"].set_response("hello")
        mock_components["llm"].set_response("Hi there!")

        orchestrator.process_single_interaction()

        # Check feedback was played for wake word
        assert FeedbackType.WAKE_WORD_DETECTED in mock_components["feedback"].events

    def test_latency_tracking(
        self, orchestrator: Orchestrator, mock_components: dict
    ) -> None:
        """Test that latency is tracked for each stage."""
        mock_components["wake_word"].schedule_detection(at_chunk=0, confidence=0.9)
        mock_components["transcriber"].set_response("test")
        mock_components["llm"].set_response("Response")

        result = orchestrator.process_single_interaction()

        # Verify latency metrics exist
        assert result is not None
        assert "stt_ms" in result.latency_breakdown
        assert "llm_ms" in result.latency_breakdown
        assert "tts_ms" in result.latency_breakdown
        assert result.total_latency_ms > 0

    def test_error_handling(
        self, orchestrator: Orchestrator, mock_components: dict
    ) -> None:
        """Test that errors are handled gracefully."""
        mock_components["wake_word"].schedule_detection(at_chunk=0, confidence=0.9)
        mock_components["transcriber"].set_error("Transcription failed")

        result = orchestrator.process_single_interaction()

        # Should handle error gracefully
        assert result is None or result.error is not None

        # Error feedback should be played
        assert FeedbackType.ERROR in mock_components["feedback"].events


class TestOrchestratorConfiguration:
    """Tests for orchestrator configuration."""

    def test_create_from_config(self) -> None:
        """Test creating orchestrator from AraConfig."""
        config = AraConfig()

        # Factory function should create orchestrator with mock components
        orch = Orchestrator.from_config(config, use_mocks=True)

        assert orch is not None
        assert orch.is_ready

    def test_start_stop(self) -> None:
        """Test starting and stopping the orchestrator."""
        config = AraConfig()
        orch = Orchestrator.from_config(config, use_mocks=True)

        orch.start()
        assert orch.is_running

        orch.stop()
        assert not orch.is_running
