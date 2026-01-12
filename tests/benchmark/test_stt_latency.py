"""STT latency benchmarks.

Measures speech-to-text transcription performance.
Target: <1.5s on Raspberry Pi 4, <0.5s on laptop.
"""

import pytest

from ara.stt import create_transcriber
from ara.stt.mock import MockTranscriber


class TestSTTLatency:
    """Benchmark tests for STT latency."""

    @pytest.fixture
    def mock_transcriber(self) -> MockTranscriber:
        """Create mock transcriber for baseline tests."""
        transcriber = MockTranscriber()
        transcriber.set_response("what time is it")
        return transcriber

    @pytest.fixture
    def sample_audio(self) -> bytes:
        """Create sample audio data (2 seconds at 16kHz, 16-bit mono)."""
        # 2 seconds * 16000 samples/sec * 2 bytes/sample
        return bytes(2 * 16000 * 2)

    @pytest.mark.benchmark
    def test_mock_transcription_latency(
        self, benchmark, mock_transcriber: MockTranscriber, sample_audio: bytes
    ) -> None:
        """Benchmark mock transcription (baseline)."""
        mock_transcriber.set_latency(0)  # Remove artificial latency

        result = benchmark(mock_transcriber.transcribe, sample_audio, 16000)

        assert result.text == "what time is it"

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_whisper_transcription_latency(self, benchmark, sample_audio: bytes) -> None:
        """Benchmark real Whisper transcription.

        This test requires faster-whisper and downloads the model.
        """
        try:
            from ara.stt.whisper import WhisperTranscriber

            transcriber = WhisperTranscriber(
                model_size="tiny.en",  # Smallest model for benchmarking
                device="cpu",
                compute_type="int8",
            )
        except RuntimeError:
            pytest.skip("faster-whisper not available")

        # Warm up (loads model)
        transcriber.transcribe(sample_audio, 16000)

        # Benchmark
        result = benchmark(transcriber.transcribe, sample_audio, 16000)

        assert result.confidence >= 0
        # Note: tiny model may not transcribe silence accurately

    @pytest.mark.benchmark
    def test_transcription_throughput(
        self, benchmark, mock_transcriber: MockTranscriber
    ) -> None:
        """Benchmark transcription throughput (calls per second)."""
        mock_transcriber.set_latency(0)

        # Various audio lengths
        audio_lengths = [16000 * 2, 32000 * 2, 48000 * 2]  # 1s, 2s, 3s

        def transcribe_multiple():
            for length in audio_lengths:
                audio = bytes(length)
                mock_transcriber.transcribe(audio, 16000)

        benchmark(transcribe_multiple)
