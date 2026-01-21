"""Unit tests for ElevenLabs TTS synthesizer."""

from unittest.mock import MagicMock, patch

import pytest


class TestElevenLabsSynthesizer:
    """Tests for ElevenLabsSynthesizer class."""

    def test_import_with_elevenlabs_available(self) -> None:
        """Test that module imports correctly when elevenlabs is installed."""
        from ara.tts.elevenlabs import ELEVENLABS_AVAILABLE, ElevenLabsSynthesizer

        assert ElevenLabsSynthesizer is not None
        # ELEVENLABS_AVAILABLE depends on whether elevenlabs is installed
        assert isinstance(ELEVENLABS_AVAILABLE, bool)

    def test_emotion_enum_values(self) -> None:
        """Test Emotion enum has expected values."""
        from ara.tts.elevenlabs import Emotion

        assert hasattr(Emotion, "NEUTRAL")
        assert hasattr(Emotion, "WARM")
        assert hasattr(Emotion, "CHEERFUL")
        assert hasattr(Emotion, "CALM")
        assert hasattr(Emotion, "CONCERNED")
        assert hasattr(Emotion, "ENTHUSIASTIC")
        assert hasattr(Emotion, "PROFESSIONAL")

    def test_emotion_cues_mapping(self) -> None:
        """Test EMOTION_CUES has entries for all emotions."""
        from ara.tts.elevenlabs import EMOTION_CUES, Emotion

        for emotion in Emotion:
            assert emotion in EMOTION_CUES
        # Neutral should have empty cue
        assert EMOTION_CUES[Emotion.NEUTRAL] == ""
        # Others should have descriptive cues
        assert "warmly" in EMOTION_CUES[Emotion.WARM]
        assert "cheerfully" in EMOTION_CUES[Emotion.CHEERFUL]

    def test_init_without_api_key(self) -> None:
        """Test initialization without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("ara.tts.elevenlabs.ELEVENLABS_AVAILABLE", True):
                from ara.tts.elevenlabs import ElevenLabsSynthesizer

                synth = ElevenLabsSynthesizer(api_key=None)
                assert not synth.is_available

    def test_init_with_placeholder_api_key(self) -> None:
        """Test that placeholder API key is not considered valid."""
        with patch("ara.tts.elevenlabs.ELEVENLABS_AVAILABLE", True):
            from ara.tts.elevenlabs import ElevenLabsSynthesizer

            synth = ElevenLabsSynthesizer(api_key="your-elevenlabs-api-key")
            assert not synth.is_available

    def test_default_voice_id(self) -> None:
        """Test default voice ID is Bella."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        assert ElevenLabsSynthesizer.DEFAULT_VOICE_ID == "EXAVITQu4vr4xnSDxMaL"

    def test_default_model(self) -> None:
        """Test default model is multilingual v2."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        assert ElevenLabsSynthesizer.DEFAULT_MODEL == "eleven_multilingual_v2"

    def test_target_sample_rate(self) -> None:
        """Test target sample rate matches pipeline requirements."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        assert ElevenLabsSynthesizer.TARGET_SAMPLE_RATE == 22050

    def test_available_voices(self) -> None:
        """Test VOICES dictionary has expected entries."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        voices = ElevenLabsSynthesizer.VOICES
        assert "rachel" in voices
        assert "domi" in voices
        assert "bella" in voices
        assert "josh" in voices
        assert "adam" in voices


class TestEmotionDetection:
    """Tests for automatic emotion detection from text."""

    @pytest.fixture
    def synthesizer(self) -> "ElevenLabsSynthesizer":
        """Create a synthesizer for testing emotion detection."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        return ElevenLabsSynthesizer(api_key="test-key")

    def test_greeting_detected_as_warm(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test greetings are detected as warm emotion."""
        from ara.tts.elevenlabs import Emotion

        assert synthesizer._detect_emotion("Hello! How are you?") == Emotion.WARM
        assert synthesizer._detect_emotion("Good morning!") == Emotion.WARM
        assert synthesizer._detect_emotion("Welcome back") == Emotion.WARM

    def test_excitement_detected_as_cheerful(
        self, synthesizer: "ElevenLabsSynthesizer"
    ) -> None:
        """Test exciting text is detected as cheerful emotion."""
        from ara.tts.elevenlabs import Emotion

        assert synthesizer._detect_emotion("That's great news!") == Emotion.CHEERFUL
        assert synthesizer._detect_emotion("Awesome work!") == Emotion.CHEERFUL
        assert synthesizer._detect_emotion("Excellent!") == Emotion.CHEERFUL

    def test_problems_detected_as_concerned(
        self, synthesizer: "ElevenLabsSynthesizer"
    ) -> None:
        """Test problem-related text is detected as concerned emotion."""
        from ara.tts.elevenlabs import Emotion

        assert synthesizer._detect_emotion("Sorry, there was an error") == Emotion.CONCERNED
        assert (
            synthesizer._detect_emotion("Unfortunately, the connection failed")
            == Emotion.CONCERNED
        )
        assert synthesizer._detect_emotion("There's a problem with that") == Emotion.CONCERNED

    def test_calming_detected_as_calm(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test calming text is detected as calm emotion."""
        from ara.tts.elevenlabs import Emotion

        assert synthesizer._detect_emotion("Don't worry, it's okay") == Emotion.CALM
        assert synthesizer._detect_emotion("Take your time") == Emotion.CALM
        assert synthesizer._detect_emotion("Relax, no rush") == Emotion.CALM

    def test_weather_detected_as_professional(
        self, synthesizer: "ElevenLabsSynthesizer"
    ) -> None:
        """Test weather info is detected as professional emotion."""
        from ara.tts.elevenlabs import Emotion

        assert (
            synthesizer._detect_emotion("The temperature is 72 degrees") == Emotion.PROFESSIONAL
        )
        assert synthesizer._detect_emotion("Currently sunny weather") == Emotion.PROFESSIONAL
        assert synthesizer._detect_emotion("The forecast shows rain") == Emotion.PROFESSIONAL

    def test_reminders_detected_as_enthusiastic(
        self, synthesizer: "ElevenLabsSynthesizer"
    ) -> None:
        """Test reminders are detected as enthusiastic emotion."""
        from ara.tts.elevenlabs import Emotion

        assert (
            synthesizer._detect_emotion("Reminder: call mom at 5pm") == Emotion.ENTHUSIASTIC
        )
        assert synthesizer._detect_emotion("Don't forget the meeting") == Emotion.ENTHUSIASTIC
        assert (
            synthesizer._detect_emotion("Timer set for 10 minutes") == Emotion.ENTHUSIASTIC
        )

    def test_neutral_text_returns_default(
        self, synthesizer: "ElevenLabsSynthesizer"
    ) -> None:
        """Test neutral text returns default emotion (WARM)."""
        from ara.tts.elevenlabs import Emotion

        # Default emotion is WARM
        assert synthesizer._detect_emotion("The meeting is at 3pm") == Emotion.WARM
        assert synthesizer._detect_emotion("Here is the information") == Emotion.WARM


class TestVoiceControl:
    """Tests for voice selection and control methods."""

    @pytest.fixture
    def synthesizer(self) -> "ElevenLabsSynthesizer":
        """Create a synthesizer for testing."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        return ElevenLabsSynthesizer(api_key="test-key")

    def test_set_voice_by_name(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test setting voice by name."""
        synthesizer.set_voice("josh")
        assert synthesizer._voice_id == "TxGEqnHWrfWFTfGW9XjX"

    def test_set_voice_by_id(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test setting voice by direct ID."""
        synthesizer.set_voice("custom-voice-id-123")
        assert synthesizer._voice_id == "custom-voice-id-123"

    def test_set_speed_clamped(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test speed is clamped to valid range."""
        synthesizer.set_speed(0.1)
        assert synthesizer._speed == 0.5  # Min clamp

        synthesizer.set_speed(3.0)
        assert synthesizer._speed == 2.0  # Max clamp

        synthesizer.set_speed(1.5)
        assert synthesizer._speed == 1.5  # Valid value

    def test_set_emotion(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test setting default emotion."""
        from ara.tts.elevenlabs import Emotion

        synthesizer.set_emotion(Emotion.CALM)
        assert synthesizer._default_emotion == Emotion.CALM

    def test_get_available_voices(self, synthesizer: "ElevenLabsSynthesizer") -> None:
        """Test getting available voice names."""
        voices = synthesizer.get_available_voices()
        assert "rachel" in voices
        assert "josh" in voices
        assert len(voices) == 5


class TestSynthesis:
    """Tests for actual synthesis (mocked API calls)."""

    def test_synthesis_not_available_raises(self) -> None:
        """Test synthesis raises when not available."""
        from ara.tts.elevenlabs import ElevenLabsSynthesizer

        synth = ElevenLabsSynthesizer(api_key=None)
        with pytest.raises(RuntimeError, match="not available"):
            synth.synthesize("Hello")

    def test_synthesis_with_mock_client(self) -> None:
        """Test synthesis with mocked ElevenLabs client."""
        from ara.tts.elevenlabs import Emotion

        # Create mock audio data (16-bit PCM at 22050 Hz)
        # 100ms of audio = 22050 * 0.1 * 2 bytes = 4410 bytes
        mock_audio = b"\x00\x01" * 2205

        # Mock the client
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter([mock_audio])

        with patch("ara.tts.elevenlabs.ELEVENLABS_AVAILABLE", True):
            with patch("ara.tts.elevenlabs.ElevenLabs", return_value=mock_client):
                from ara.tts.elevenlabs import ElevenLabsSynthesizer

                synth = ElevenLabsSynthesizer(api_key="real-api-key")
                synth._client = mock_client  # Force client to be our mock

                result = synth.synthesize("Hello world", emotion=Emotion.WARM)

                assert result.audio == mock_audio
                assert result.sample_rate == 22050
                assert result.duration_ms > 0
                assert result.latency_ms >= 0

                # Verify API was called with correct parameters
                mock_client.text_to_speech.convert.assert_called_once()
                call_kwargs = mock_client.text_to_speech.convert.call_args.kwargs
                assert call_kwargs["text"] == "Hello world"
                assert call_kwargs["output_format"] == "pcm_22050"
                assert call_kwargs["next_text"] == "she said warmly"

    def test_synthesis_api_error_raises_runtime_error(self) -> None:
        """Test that API errors are wrapped in RuntimeError."""
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.side_effect = Exception("API error")

        with patch("ara.tts.elevenlabs.ELEVENLABS_AVAILABLE", True):
            with patch("ara.tts.elevenlabs.ElevenLabs", return_value=mock_client):
                from ara.tts.elevenlabs import ElevenLabsSynthesizer

                synth = ElevenLabsSynthesizer(api_key="real-api-key")
                synth._client = mock_client

                with pytest.raises(RuntimeError, match="synthesis failed"):
                    synth.synthesize("Hello")


class TestExports:
    """Tests for module exports."""

    def test_all_exports(self) -> None:
        """Test __all__ contains expected exports."""
        from ara.tts import elevenlabs

        assert "ElevenLabsSynthesizer" in elevenlabs.__all__
        assert "Emotion" in elevenlabs.__all__
        assert "ELEVENLABS_AVAILABLE" in elevenlabs.__all__
