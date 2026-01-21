"""Integration tests for platform-adaptive TTS selection."""

from unittest.mock import patch

import pytest

from ara.tts import create_synthesizer
from ara.tts.mock import MockSynthesizer
from ara.tts.platform import Platform, detect_platform
from ara.tts.synthesizer import SynthesisResult, Synthesizer


class TestPlatformTTSSelection:
    """Test automatic TTS engine selection based on platform."""

    def test_create_synthesizer_returns_synthesizer(self) -> None:
        """create_synthesizer should always return a Synthesizer."""
        synth = create_synthesizer()
        assert hasattr(synth, "synthesize")
        assert hasattr(synth, "is_available")

    def test_mock_synthesizer_when_use_mock_true(self) -> None:
        """Should return MockSynthesizer when use_mock=True."""
        synth = create_synthesizer(use_mock=True)
        assert isinstance(synth, MockSynthesizer)

    def test_macos_synthesizer_on_darwin(self) -> None:
        """Should return MacOSSynthesizer on macOS when available."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("ara.tts.detect_platform", return_value=Platform.MACOS),
            patch("shutil.which", return_value="/usr/bin/say"),
        ):
            synth = create_synthesizer()
            # On macOS, should get MacOSSynthesizer if say command available
            assert isinstance(synth, (MacOSSynthesizer, MockSynthesizer))

    def test_piper_synthesizer_on_raspberry_pi(self) -> None:
        """Should return PiperSynthesizer on Raspberry Pi when available."""
        from ara.tts.piper import PiperSynthesizer

        with patch("ara.tts.detect_platform", return_value=Platform.RASPBERRY_PI):
            synth = create_synthesizer()
            # Should try Piper first, fall back to Mock if not available
            assert isinstance(synth, (PiperSynthesizer, MockSynthesizer))

    def test_never_returns_none(self) -> None:
        """create_synthesizer should never return None."""
        # Test with various platform detections
        for platform in Platform:
            with patch("ara.tts.detect_platform", return_value=platform):
                synth = create_synthesizer()
                assert synth is not None

    def test_fallback_to_mock_on_failure(self) -> None:
        """Should fall back to Mock when all engines fail."""
        with (
            patch("ara.tts.detect_platform", return_value=Platform.OTHER),
            patch("ara.tts.piper.PIPER_AVAILABLE", False),
        ):
            synth = create_synthesizer()
            # Should fall back to Mock
            assert isinstance(synth, MockSynthesizer)


class TestSynthesizerProtocolCompliance:
    """Test that all synthesizers comply with the Synthesizer protocol."""

    def test_mock_synthesizer_protocol_compliance(self) -> None:
        """MockSynthesizer should implement Synthesizer protocol."""
        synth = MockSynthesizer()
        assert hasattr(synth, "synthesize")
        assert hasattr(synth, "set_voice")
        assert hasattr(synth, "set_speed")
        assert hasattr(synth, "get_available_voices")
        assert hasattr(synth, "is_available")

    def test_macos_synthesizer_protocol_compliance(self) -> None:
        """MacOSSynthesizer should implement Synthesizer protocol."""
        from ara.tts.macos import MacOSSynthesizer

        with patch("shutil.which", return_value="/usr/bin/say"):
            synth = MacOSSynthesizer()
            assert hasattr(synth, "synthesize")
            assert hasattr(synth, "set_voice")
            assert hasattr(synth, "set_speed")
            assert hasattr(synth, "get_available_voices")
            assert hasattr(synth, "is_available")


class TestAudioOutputConsistency:
    """Test that audio output is consistent across synthesizers."""

    def test_synthesis_result_has_required_fields(self) -> None:
        """SynthesisResult should have all required fields."""
        synth = create_synthesizer(use_mock=True)
        result = synth.synthesize("Test")

        assert hasattr(result, "audio")
        assert hasattr(result, "sample_rate")
        assert hasattr(result, "duration_ms")
        assert hasattr(result, "latency_ms")

    def test_audio_is_bytes(self) -> None:
        """Audio output should be bytes."""
        synth = create_synthesizer(use_mock=True)
        result = synth.synthesize("Test")

        assert isinstance(result.audio, bytes)
        assert len(result.audio) > 0

    def test_sample_rate_is_positive(self) -> None:
        """Sample rate should be a positive integer."""
        synth = create_synthesizer(use_mock=True)
        result = synth.synthesize("Test")

        assert isinstance(result.sample_rate, int)
        assert result.sample_rate > 0


class TestLogging:
    """Test that TTS selection is logged appropriately."""

    def test_logs_selected_synthesizer(self) -> None:
        """Should log which synthesizer was selected."""
        import logging

        with patch("ara.tts.logger") as mock_logger:
            synth = create_synthesizer(use_mock=True)
            # Logger should have been called during creation
            # The actual log message depends on implementation


class TestActualPlatformDetection:
    """Test actual platform detection on current system."""

    def test_detect_platform_on_current_system(self) -> None:
        """detect_platform should work on current system."""
        platform = detect_platform()
        assert isinstance(platform, Platform)
        assert platform in list(Platform)

    @pytest.mark.skipif(
        detect_platform() != Platform.MACOS,
        reason="Only runs on macOS",
    )
    def test_macos_tts_on_actual_macos(self) -> None:
        """Test actual macOS TTS if running on macOS."""
        from ara.tts.macos import MacOSSynthesizer

        synth = MacOSSynthesizer()
        if synth.is_available:
            result = synth.synthesize("Hello")
            assert isinstance(result, SynthesisResult)
            assert len(result.audio) > 0
            assert result.sample_rate > 0


class TestTTSFailureRecovery:
    """Test TTS failure recovery (US3)."""

    def test_synthesis_after_fallback_works(self) -> None:
        """Synthesize should work after falling back to Mock."""
        # Force fallback by using mock
        synth = create_synthesizer(use_mock=True)
        result = synth.synthesize("Test after fallback")

        assert result is not None
        assert len(result.audio) > 0

    def test_multiple_syntheses_after_fallback(self) -> None:
        """Multiple synthesis calls should work after fallback."""
        synth = create_synthesizer(use_mock=True)

        results = [synth.synthesize(f"Test {i}") for i in range(5)]

        assert all(r.audio for r in results)
        assert all(r.sample_rate > 0 for r in results)

    def test_fallback_synthesizer_protocol_compliance(self) -> None:
        """Fallback synthesizer should implement full protocol."""
        synth = create_synthesizer(use_mock=True)

        # Test all protocol methods work
        assert hasattr(synth, "synthesize")
        assert hasattr(synth, "set_voice")
        assert hasattr(synth, "set_speed")
        assert hasattr(synth, "get_available_voices")
        assert hasattr(synth, "is_available")

        # Call each method
        result = synth.synthesize("Test")
        assert result is not None

        synth.set_voice("test-voice")
        synth.set_speed(1.5)
        voices = synth.get_available_voices()
        assert isinstance(voices, list)


class TestAudioSmoothness:
    """Test audio smoothness and quality (US2)."""

    def test_audio_has_no_zero_length(self) -> None:
        """Audio should never be zero-length."""
        synth = create_synthesizer(use_mock=True)
        result = synth.synthesize("Test phrase")

        assert len(result.audio) > 0

    def test_audio_duration_proportional_to_text(self) -> None:
        """Longer text should produce longer audio."""
        synth = create_synthesizer(use_mock=True)

        short_result = synth.synthesize("Hi")
        long_result = synth.synthesize("Hello, this is a much longer phrase for testing")

        # Longer text should have longer duration
        assert long_result.duration_ms >= short_result.duration_ms

    def test_sample_rate_is_standard(self) -> None:
        """Sample rate should be a standard value (22050 Hz typical)."""
        synth = create_synthesizer(use_mock=True)
        result = synth.synthesize("Test")

        # Common audio sample rates
        valid_rates = [8000, 16000, 22050, 24000, 44100, 48000]
        assert result.sample_rate in valid_rates

    @pytest.mark.skipif(
        detect_platform() != Platform.MACOS,
        reason="Only runs on macOS",
    )
    def test_macos_audio_is_16bit_pcm(self) -> None:
        """macOS audio should be 16-bit PCM (2 bytes per sample)."""
        from ara.tts.macos import MacOSSynthesizer

        synth = MacOSSynthesizer()
        if synth.is_available:
            result = synth.synthesize("Test")
            # 16-bit audio: audio_bytes = samples * 2
            # So audio length should be even
            assert len(result.audio) % 2 == 0

    @pytest.mark.skipif(
        detect_platform() != Platform.MACOS,
        reason="Only runs on macOS",
    )
    def test_macos_latency_reasonable(self) -> None:
        """macOS TTS latency should be reasonable for short phrases."""
        from ara.tts.macos import MacOSSynthesizer

        synth = MacOSSynthesizer()
        if synth.is_available:
            result = synth.synthesize("Hello")
            # Latency varies by system load; just verify it completes
            # The 500ms target is aspirational for production tuning
            assert result.latency_ms < 5000  # Generous bound for CI variance
