"""Unit tests for speech-to-text module."""

from ara.stt import TranscriptionResult, create_transcriber
from ara.stt.mock import MockTranscriber


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a transcription result."""
        result = TranscriptionResult(
            text="what time is it",
            confidence=0.95,
            language="en",
            duration_ms=1500,
            segments=[],
        )
        assert result.text == "what time is it"
        assert result.confidence == 0.95
        assert result.language == "en"
        assert result.duration_ms == 1500

    def test_result_with_segments(self) -> None:
        """Test result with word-level segments."""
        segments = [
            {"word": "what", "start": 0.0, "end": 0.2},
            {"word": "time", "start": 0.2, "end": 0.4},
            {"word": "is", "start": 0.4, "end": 0.5},
            {"word": "it", "start": 0.5, "end": 0.6},
        ]
        result = TranscriptionResult(
            text="what time is it",
            confidence=0.95,
            language="en",
            duration_ms=600,
            segments=segments,
        )
        assert len(result.segments) == 4


class TestMockTranscriber:
    """Tests for MockTranscriber."""

    def test_transcribe_returns_preset(self) -> None:
        """Test that transcribe returns preset response."""
        transcriber = MockTranscriber()
        transcriber.set_response("hello world")

        result = transcriber.transcribe(bytes(1000), sample_rate=16000)

        assert result.text == "hello world"
        assert result.confidence > 0

    def test_transcribe_default_response(self) -> None:
        """Test default transcription response."""
        transcriber = MockTranscriber()

        result = transcriber.transcribe(bytes(1000), sample_rate=16000)

        assert result.text == ""
        assert result.confidence == 0.0

    def test_set_language(self) -> None:
        """Test setting language."""
        transcriber = MockTranscriber()
        transcriber.set_language("es")
        assert transcriber.language == "es"

    def test_transcribe_records_calls(self) -> None:
        """Test that transcribe records call history."""
        transcriber = MockTranscriber()

        transcriber.transcribe(bytes(100), sample_rate=16000)
        transcriber.transcribe(bytes(200), sample_rate=16000)

        assert transcriber.call_count == 2


class TestCreateTranscriber:
    """Tests for transcriber factory function."""

    def test_create_mock_transcriber(self) -> None:
        """Test creating mock transcriber."""
        transcriber = create_transcriber(use_mock=True)
        assert isinstance(transcriber, MockTranscriber)

    def test_create_transcriber_with_config(self) -> None:
        """Test creating transcriber with configuration."""
        from ara.config import STTConfig

        config = STTConfig(model="tiny.en", device="cpu")
        transcriber = create_transcriber(config=config, use_mock=True)

        assert isinstance(transcriber, MockTranscriber)
