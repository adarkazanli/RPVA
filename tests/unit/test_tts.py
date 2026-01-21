"""Unit tests for text-to-speech module."""

from ara.tts import SynthesisResult, create_synthesizer
from ara.tts.mock import MockSynthesizer


class TestSynthesisResult:
    """Tests for SynthesisResult dataclass."""

    def test_create_result(self) -> None:
        """Test creating a synthesis result."""
        result = SynthesisResult(
            audio=bytes(1000),
            sample_rate=22050,
            duration_ms=500,
            latency_ms=100,
        )
        assert len(result.audio) == 1000
        assert result.sample_rate == 22050
        assert result.duration_ms == 500
        assert result.latency_ms == 100


class TestMockSynthesizer:
    """Tests for MockSynthesizer."""

    def test_synthesize_returns_audio(self) -> None:
        """Test that synthesize returns audio data."""
        synth = MockSynthesizer()

        result = synth.synthesize("Hello world")

        assert len(result.audio) > 0
        assert result.sample_rate > 0
        assert result.duration_ms > 0

    def test_synthesize_longer_text_longer_audio(self) -> None:
        """Test that longer text produces longer audio."""
        synth = MockSynthesizer()

        short_result = synth.synthesize("Hi")
        long_result = synth.synthesize("Hello, how are you doing today?")

        assert long_result.duration_ms > short_result.duration_ms

    def test_set_voice(self) -> None:
        """Test setting voice."""
        synth = MockSynthesizer()
        synth.set_voice("en_US-amy-medium")
        assert synth.voice == "en_US-amy-medium"

    def test_set_speed(self) -> None:
        """Test setting speech speed."""
        synth = MockSynthesizer()
        synth.set_speed(1.5)
        assert synth.speed == 1.5

    def test_get_available_voices(self) -> None:
        """Test getting available voices."""
        synth = MockSynthesizer()

        voices = synth.get_available_voices()

        assert isinstance(voices, list)
        assert len(voices) > 0

    def test_synthesize_records_calls(self) -> None:
        """Test that synthesize records call history."""
        synth = MockSynthesizer()

        synth.synthesize("Hello")
        synth.synthesize("World")

        assert synth.call_count == 2

    def test_synthesized_texts(self) -> None:
        """Test tracking synthesized texts."""
        synth = MockSynthesizer()

        synth.synthesize("Hello")
        synth.synthesize("World")

        assert synth.synthesized_texts == ["Hello", "World"]


class TestCreateSynthesizer:
    """Tests for synthesizer factory function."""

    def test_create_mock_synthesizer(self) -> None:
        """Test creating mock synthesizer."""
        synth = create_synthesizer(use_mock=True)
        assert isinstance(synth, MockSynthesizer)

    def test_create_synthesizer_with_config(self) -> None:
        """Test creating synthesizer with configuration."""
        from ara.config import TTSConfig

        config = TTSConfig(
            voice="en_US-lessac-medium",
            speed=1.2,
        )
        synth = create_synthesizer(config=config, use_mock=True)

        assert isinstance(synth, MockSynthesizer)


class TestFallbackChain:
    """Test fallback chain in create_synthesizer (US3)."""

    def test_macos_fallback_to_mock_when_all_unavailable(self) -> None:
        """Should fall back to Mock when macOS and Piper unavailable."""
        from unittest.mock import patch

        from ara.tts.platform import Platform

        with (
            patch("ara.tts.detect_platform", return_value=Platform.MACOS),
            patch("shutil.which", return_value=None),  # say not available
            patch("ara.tts.piper.PIPER_AVAILABLE", False),  # Piper not available
        ):
            synth = create_synthesizer()
            # Should fall back to Mock since both macOS and Piper unavailable
            assert isinstance(synth, MockSynthesizer)

    def test_raspberry_pi_fallback_to_mock(self) -> None:
        """Should fall back to Mock when Piper unavailable on Pi."""
        from unittest.mock import patch

        from ara.tts.platform import Platform

        with (
            patch("ara.tts.detect_platform", return_value=Platform.RASPBERRY_PI),
            patch("ara.tts.piper.PIPER_AVAILABLE", False),
        ):
            synth = create_synthesizer()
            assert isinstance(synth, MockSynthesizer)

    def test_other_platform_fallback_to_mock(self) -> None:
        """Should fall back to Mock on other platforms when Piper unavailable."""
        from unittest.mock import patch

        from ara.tts.platform import Platform

        with (
            patch("ara.tts.detect_platform", return_value=Platform.OTHER),
            patch("ara.tts.piper.PIPER_AVAILABLE", False),
        ):
            synth = create_synthesizer()
            assert isinstance(synth, MockSynthesizer)

    def test_never_returns_none(self) -> None:
        """create_synthesizer should never return None."""
        from unittest.mock import patch

        from ara.tts.platform import Platform

        # Even with all TTS engines failing
        with (
            patch("ara.tts.detect_platform", return_value=Platform.OTHER),
            patch("ara.tts.piper.PIPER_AVAILABLE", False),
        ):
            synth = create_synthesizer()
            assert synth is not None

    def test_mock_always_available_as_final_fallback(self) -> None:
        """MockSynthesizer should always be available as final fallback."""
        mock = MockSynthesizer()
        assert mock.is_available is True

    def test_use_mock_bypasses_detection(self) -> None:
        """use_mock=True should bypass platform detection entirely."""
        synth = create_synthesizer(use_mock=True)
        assert isinstance(synth, MockSynthesizer)


class TestExceptionHandling:
    """Test exception handling in create_synthesizer (US3)."""

    def test_handles_piper_init_exception(self) -> None:
        """Should handle exceptions during PiperSynthesizer initialization."""
        from unittest.mock import patch

        from ara.tts.platform import Platform

        with (
            patch("ara.tts.detect_platform", return_value=Platform.RASPBERRY_PI),
            patch("ara.tts.piper.PiperSynthesizer", side_effect=Exception("Init failed")),
        ):
            synth = create_synthesizer()
            # Should fall back to Mock
            assert isinstance(synth, MockSynthesizer)
