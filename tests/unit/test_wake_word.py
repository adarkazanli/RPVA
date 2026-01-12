"""Unit tests for wake word detection module."""



from ara.audio import AudioChunk
from ara.wake_word import WakeWordResult, create_wake_word_detector
from ara.wake_word.mock import MockWakeWordDetector


class TestWakeWordResult:
    """Tests for WakeWordResult dataclass."""

    def test_detected_result(self) -> None:
        """Test creating a detected wake word result."""
        result = WakeWordResult(
            detected=True,
            confidence=0.95,
            keyword="ara",
            timestamp_ms=1000,
        )
        assert result.detected is True
        assert result.confidence == 0.95
        assert result.keyword == "ara"

    def test_not_detected_result(self) -> None:
        """Test creating a not-detected result."""
        result = WakeWordResult(
            detected=False,
            confidence=0.0,
            keyword="",
            timestamp_ms=500,
        )
        assert result.detected is False
        assert result.confidence == 0.0


class TestMockWakeWordDetector:
    """Tests for MockWakeWordDetector."""

    def test_initialize(self) -> None:
        """Test detector initialization."""
        detector = MockWakeWordDetector()
        detector.initialize(keywords=["ara"], sensitivity=0.5)
        assert detector.keywords == ["ara"]
        assert detector.sensitivity == 0.5

    def test_process_no_detection(self) -> None:
        """Test processing audio with no wake word."""
        detector = MockWakeWordDetector()
        detector.initialize(keywords=["ara"], sensitivity=0.5)

        chunk = AudioChunk(
            data=bytes(1024),
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp_ms=0,
        )

        result = detector.process(chunk)
        assert result.detected is False

    def test_process_with_scheduled_detection(self) -> None:
        """Test detection when wake word is scheduled."""
        detector = MockWakeWordDetector()
        detector.initialize(keywords=["ara"], sensitivity=0.5)
        detector.schedule_detection(at_chunk=1, confidence=0.9)

        chunk = AudioChunk(
            data=bytes(1024),
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp_ms=0,
        )

        # First chunk - no detection
        result1 = detector.process(chunk)
        assert result1.detected is False

        # Second chunk - detection scheduled
        result2 = detector.process(chunk)
        assert result2.detected is True
        assert result2.confidence == 0.9
        assert result2.keyword == "ara"

    def test_cleanup(self) -> None:
        """Test cleanup releases resources."""
        detector = MockWakeWordDetector()
        detector.initialize(keywords=["ara"], sensitivity=0.5)
        detector.cleanup()
        # Should be able to reinitialize after cleanup
        detector.initialize(keywords=["hey"], sensitivity=0.7)


class TestWakeWordDetectorProtocol:
    """Tests for WakeWordDetector protocol compliance."""

    def test_mock_implements_protocol(self) -> None:
        """Test that MockWakeWordDetector implements WakeWordDetector protocol."""
        detector = MockWakeWordDetector()
        # Protocol check - these methods should exist
        assert hasattr(detector, "initialize")
        assert hasattr(detector, "process")
        assert hasattr(detector, "cleanup")
        assert callable(detector.initialize)
        assert callable(detector.process)
        assert callable(detector.cleanup)


class TestCreateWakeWordDetector:
    """Tests for wake word detector factory function."""

    def test_create_mock_detector(self) -> None:
        """Test creating mock detector."""
        detector = create_wake_word_detector(use_mock=True)
        assert isinstance(detector, MockWakeWordDetector)

    def test_create_detector_with_config(self) -> None:
        """Test creating detector with configuration."""
        from ara.config import WakeWordConfig

        config = WakeWordConfig(keyword="ara", sensitivity=0.6)
        detector = create_wake_word_detector(config=config, use_mock=True)

        # Mock detector should have config applied after initialize
        detector.initialize(keywords=[config.keyword], sensitivity=config.sensitivity)
        assert detector.sensitivity == 0.6
