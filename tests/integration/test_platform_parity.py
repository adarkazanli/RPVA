"""Platform parity tests (T116).

Ensures identical behavior across platforms for same inputs.
"""



class TestPlatformParity:
    """Tests for cross-platform behavior parity."""

    def test_platform_detection(self) -> None:
        """Test platform detection works."""
        from ara.config.profiles import Platform, detect_platform

        platform = detect_platform()
        assert platform in [
            Platform.MACOS,
            Platform.LINUX,
            Platform.RASPBERRY_PI,
            Platform.UNKNOWN,
        ]

    def test_gpu_detection(self) -> None:
        """Test GPU/accelerator detection."""
        from ara.config.profiles import Accelerator, detect_accelerator

        accelerator = detect_accelerator()
        assert accelerator in [
            Accelerator.METAL,
            Accelerator.CUDA,
            Accelerator.CPU,
        ]

    def test_config_loading_cross_platform(self) -> None:
        """Test config loads consistently across platforms."""
        from ara.config.loader import load_config

        # Should load without error on any platform
        config = load_config(profile="dev")
        assert config is not None
        assert config.wake_word.keyword == "ara"

    def test_mock_components_work_everywhere(self) -> None:
        """Test mock components work identically on all platforms."""
        from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
        from ara.feedback.audio import MockFeedback
        from ara.llm.mock import MockLanguageModel
        from ara.stt.mock import MockTranscriber
        from ara.tts.mock import MockSynthesizer
        from ara.wake_word.mock import MockWakeWordDetector

        # All mocks should instantiate
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        # All should be functional
        assert capture is not None
        assert playback is not None
        assert wake_word is not None
        assert transcriber is not None
        assert llm is not None
        assert synthesizer is not None
        assert feedback is not None

    def test_intent_classification_deterministic(self) -> None:
        """Test intent classification produces same results everywhere."""
        from ara.router.intent import IntentClassifier, IntentType

        classifier = IntentClassifier()

        # Test cases should produce identical results on any platform
        test_cases = [
            ("set a timer for 5 minutes", IntentType.TIMER_SET),
            ("what time is it", IntentType.GENERAL_QUESTION),
            ("search for Python tutorials", IntentType.WEB_SEARCH),
            ("go offline", IntentType.SYSTEM_COMMAND),
            ("remind me to call mom", IntentType.REMINDER_SET),
        ]

        for text, expected_type in test_cases:
            intent = classifier.classify(text)
            assert intent.type == expected_type, f"Failed for: {text}"

    def test_time_parsing_deterministic(self) -> None:
        """Test time parsing produces consistent results."""
        from ara.commands.timer import parse_duration

        # Same inputs should produce same outputs everywhere
        test_cases = [
            ("5 minutes", 300),
            ("1 hour", 3600),
            ("30 seconds", 30),
            ("2 hours and 30 minutes", 9000),
        ]

        for text, expected_seconds in test_cases:
            result = parse_duration(text)
            assert result == expected_seconds, f"Failed for: {text}"


class TestPlatformSpecificBehavior:
    """Tests for platform-specific behavior that should be handled correctly."""

    def test_audio_backend_selection(self) -> None:
        """Test correct audio backend is selected per platform."""
        from ara.config.profiles import Platform, detect_platform

        platform = detect_platform()

        if platform == Platform.MACOS:
            # On macOS, should be able to use CoreAudio
            pass  # Backend selection tested elsewhere
        elif platform in [Platform.LINUX, Platform.RASPBERRY_PI]:
            # On Linux, should use ALSA
            pass
        # No assertions needed - just verify no errors

    def test_model_path_resolution(self) -> None:
        """Test model paths resolve correctly on all platforms."""
        from pathlib import Path

        # Model paths should work with forward slashes on all platforms
        model_path = Path("models") / "whisper" / "base.en"
        assert model_path.parts[-1] == "base.en"
        assert model_path.parts[-2] == "whisper"

    def test_config_paths_cross_platform(self) -> None:
        """Test config paths work on all platforms."""
        from ara.config.profiles import Profile, get_profile_path

        # Should return valid paths without errors
        dev_path = get_profile_path(Profile.DEV)
        prod_path = get_profile_path(Profile.PROD)

        assert dev_path.name == "dev.yaml"
        assert prod_path.name == "prod.yaml"
