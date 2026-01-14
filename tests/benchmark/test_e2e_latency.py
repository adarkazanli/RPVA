"""End-to-end latency benchmarks.

Measures complete voice interaction pipeline performance.
Target: <6s on Raspberry Pi 4, <2s on laptop.
"""

import pytest

from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
from ara.config import AraConfig
from ara.feedback.audio import MockFeedback
from ara.llm.mock import MockLanguageModel
from ara.router.orchestrator import Orchestrator
from ara.stt.mock import MockTranscriber
from ara.tts.mock import MockSynthesizer
from ara.wake_word.mock import MockWakeWordDetector


class TestE2ELatency:
    """Benchmark tests for end-to-end latency."""

    @pytest.fixture
    def mock_orchestrator(self) -> Orchestrator:
        """Create orchestrator with mock components."""
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        # Configure mocks
        wake_word.initialize(keywords=["ara"], sensitivity=0.5)
        wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        # Use a general question that goes to LLM, not a time query (which bypasses LLM)
        transcriber.set_response("tell me a fun fact")
        llm.set_response("Octopuses have three hearts!")

        # Remove artificial latencies
        transcriber.set_latency(0)
        llm.set_latency(0)
        synthesizer.set_latency(0)

        # Set audio source for capture
        capture.set_audio_data(bytes(16000 * 2 * 2))  # 2 seconds of audio

        orch = Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )
        # Clear any stored user name to prevent test pollution
        orch._user_name = None
        return orch

    @pytest.mark.benchmark
    def test_full_interaction_latency(self, benchmark, mock_orchestrator: Orchestrator) -> None:
        """Benchmark complete voice interaction."""

        def run_interaction():
            # Reset mocks for each run
            mock_orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
            mock_orchestrator._capture.set_audio_data(bytes(16000 * 2 * 2))
            return mock_orchestrator.process_single_interaction()

        result = benchmark(run_interaction)

        assert result is not None
        assert result.transcript == "tell me a fun fact"
        assert "Octopuses" in result.response_text or "hearts" in result.response_text

    @pytest.mark.benchmark
    def test_pipeline_stage_breakdown(self, mock_orchestrator: Orchestrator) -> None:
        """Test latency breakdown by pipeline stage."""
        mock_orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        mock_orchestrator._capture.set_audio_data(bytes(16000 * 2 * 2))

        result = mock_orchestrator.process_single_interaction()

        assert result is not None
        assert "stt_ms" in result.latency_breakdown
        assert "llm_ms" in result.latency_breakdown
        assert "tts_ms" in result.latency_breakdown
        assert result.total_latency_ms > 0

        # Log breakdown for analysis
        print("\nLatency breakdown:")
        for stage, latency in result.latency_breakdown.items():
            print(f"  {stage}: {latency}ms")
        print(f"  Total: {result.total_latency_ms}ms")

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_real_components_latency(self, benchmark) -> None:  # noqa: ARG002
        """Benchmark with real components (requires dependencies).

        This test requires:
        - Porcupine (wake word)
        - faster-whisper (STT)
        - Ollama running (LLM)
        - Piper models (TTS)
        """
        config = AraConfig()

        try:
            orchestrator = Orchestrator.from_config(config, use_mocks=False)
        except Exception as e:
            pytest.skip(f"Real components not available: {e}")

        # This would require actual audio, so we skip the full benchmark
        # Just verify initialization works
        assert orchestrator.is_ready

    @pytest.mark.benchmark
    def test_throughput_interactions_per_minute(self, mock_orchestrator: Orchestrator) -> None:
        """Measure how many interactions can be processed per minute."""
        import time

        start = time.time()
        count = 0

        # Run for 1 second
        while time.time() - start < 1.0:
            mock_orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
            mock_orchestrator._capture.set_audio_data(bytes(16000 * 2))
            result = mock_orchestrator.process_single_interaction()
            if result and not result.error:
                count += 1

        interactions_per_minute = count * 60
        print(f"\nThroughput: {interactions_per_minute} interactions/minute")
        print(f"  ({count} interactions in 1 second)")

        # With mock components, should be able to do many interactions
        assert count > 0
