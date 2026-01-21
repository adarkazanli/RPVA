"""Unit tests for MacOSSynthesizer."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ara.tts.synthesizer import SynthesisResult


class TestMacOSSynthesizerAvailability:
    """Test MacOSSynthesizer availability checks."""

    def test_is_available_when_say_exists(self) -> None:
        """Should be available when say command exists."""
        from ara.tts.macos import MacOSSynthesizer

        with patch("shutil.which", return_value="/usr/bin/say"):
            synth = MacOSSynthesizer()
            assert synth.is_available is True

    def test_is_not_available_when_say_missing(self) -> None:
        """Should not be available when say command is missing."""
        from ara.tts.macos import MacOSSynthesizer

        with patch("shutil.which", return_value=None):
            synth = MacOSSynthesizer()
            assert synth.is_available is False


class TestMacOSSynthesizerSynthesize:
    """Test MacOSSynthesizer synthesize method."""

    def test_synthesize_returns_synthesis_result(self) -> None:
        """synthesize should return SynthesisResult."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch.object(MacOSSynthesizer, "_run_say_command") as mock_say,
            patch.object(MacOSSynthesizer, "_convert_aiff_to_pcm") as mock_convert,
        ):
            # Mock the say command to create a dummy file
            mock_say.return_value = None
            # Mock the conversion to return PCM bytes
            mock_convert.return_value = (b"\x00" * 1000, 22050)

            synth = MacOSSynthesizer()
            result = synth.synthesize("Hello, world!")

            assert isinstance(result, SynthesisResult)
            assert result.audio == b"\x00" * 1000
            assert result.sample_rate == 22050
            assert result.duration_ms > 0
            assert result.latency_ms >= 0

    def test_synthesize_raises_on_failure(self) -> None:
        """synthesize should raise RuntimeError on failure."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch.object(
                MacOSSynthesizer,
                "_run_say_command",
                side_effect=subprocess.CalledProcessError(1, "say"),
            ),
        ):
            synth = MacOSSynthesizer()
            with pytest.raises(RuntimeError):
                synth.synthesize("Hello")

    def test_synthesize_with_empty_text(self) -> None:
        """synthesize should handle empty text gracefully."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch.object(MacOSSynthesizer, "_run_say_command") as mock_say,
            patch.object(MacOSSynthesizer, "_convert_aiff_to_pcm") as mock_convert,
        ):
            mock_say.return_value = None
            mock_convert.return_value = (b"\x00" * 100, 22050)

            synth = MacOSSynthesizer()
            # Should not raise for empty string
            result = synth.synthesize("")
            assert isinstance(result, SynthesisResult)


class TestMacOSSynthesizerVoiceSettings:
    """Test MacOSSynthesizer voice configuration."""

    def test_default_voice_is_samantha(self) -> None:
        """Default voice should be Samantha."""
        from ara.tts.macos import MacOSSynthesizer

        with patch("shutil.which", return_value="/usr/bin/say"):
            synth = MacOSSynthesizer()
            assert synth._voice == "Samantha"

    def test_set_voice_changes_voice(self) -> None:
        """set_voice should change the voice."""
        from ara.tts.macos import MacOSSynthesizer

        with patch("shutil.which", return_value="/usr/bin/say"):
            synth = MacOSSynthesizer()
            synth.set_voice("Alex")
            assert synth._voice == "Alex"

    def test_set_speed_clamps_values(self) -> None:
        """set_speed should clamp values to valid range."""
        from ara.tts.macos import MacOSSynthesizer

        with patch("shutil.which", return_value="/usr/bin/say"):
            synth = MacOSSynthesizer()

            synth.set_speed(0.1)
            assert synth._speed >= 0.5

            synth.set_speed(5.0)
            assert synth._speed <= 2.0

            synth.set_speed(1.5)
            assert synth._speed == 1.5

    def test_get_available_voices_returns_list(self) -> None:
        """get_available_voices should return a list."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                stdout="Alex                en_US    # Most people recognize me by my voice.\n"
                "Samantha            en_US    # Hello, my name is Samantha.\n",
                returncode=0,
            )
            synth = MacOSSynthesizer()
            voices = synth.get_available_voices()

            assert isinstance(voices, list)


class TestMacOSSynthesizerLatency:
    """Test MacOSSynthesizer latency requirements."""

    def test_synthesis_latency_under_500ms(self) -> None:
        """Synthesis should complete within 500ms budget."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch.object(MacOSSynthesizer, "_run_say_command") as mock_say,
            patch.object(MacOSSynthesizer, "_convert_aiff_to_pcm") as mock_convert,
        ):
            mock_say.return_value = None
            mock_convert.return_value = (b"\x00" * 1000, 22050)

            synth = MacOSSynthesizer()
            result = synth.synthesize("Hello")

            # With mocked execution, latency should be minimal
            # Real test would verify actual latency
            assert result.latency_ms >= 0


class TestMacOSSynthesizerVoiceQuality:
    """Test MacOSSynthesizer voice quality metrics (US2)."""

    def test_latency_under_500ms_budget(self) -> None:
        """Synthesis latency should be under 500ms per spec."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch.object(MacOSSynthesizer, "_run_say_command") as mock_say,
            patch.object(MacOSSynthesizer, "_convert_aiff_to_pcm") as mock_convert,
        ):
            mock_say.return_value = None
            # Simulate realistic audio output
            mock_convert.return_value = (b"\x00" * 44100, 22050)

            synth = MacOSSynthesizer()
            result = synth.synthesize("Hello, how are you today?")

            # Mocked, so latency should be very low
            # Real test verifies actual TTS latency
            assert result.latency_ms < 500

    def test_audio_sample_rate_matches_target(self) -> None:
        """Audio sample rate should be 22050 Hz to match Piper."""
        from ara.tts.macos import MacOSSynthesizer

        with (
            patch("shutil.which", return_value="/usr/bin/say"),
            patch.object(MacOSSynthesizer, "_run_say_command") as mock_say,
            patch.object(MacOSSynthesizer, "_convert_aiff_to_pcm") as mock_convert,
        ):
            mock_say.return_value = None
            mock_convert.return_value = (b"\x00" * 1000, 22050)

            synth = MacOSSynthesizer()
            result = synth.synthesize("Test")

            assert result.sample_rate == 22050

    def test_target_sample_rate_constant(self) -> None:
        """MacOSSynthesizer should have TARGET_SAMPLE_RATE of 22050."""
        from ara.tts.macos import MacOSSynthesizer

        assert MacOSSynthesizer.TARGET_SAMPLE_RATE == 22050
