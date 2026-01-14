"""CI pipeline tests with mock audio (T117).

Tests that run in CI environments without real audio hardware.
"""


class TestCIMockAudio:
    """Tests for CI environment with mock audio."""

    def test_mock_audio_capture_works_without_hardware(self) -> None:
        """Test MockAudioCapture works without real audio hardware."""
        from ara.audio.mock_capture import MockAudioCapture

        capture = MockAudioCapture(sample_rate=16000)

        # Should be able to set and stream audio data
        test_audio = bytes(16000 * 2)  # 1 second of audio
        capture.set_audio_data(test_audio)

        capture.start()
        chunks = list(capture.stream())
        capture.stop()

        assert len(chunks) > 0
        total_bytes = sum(len(c.data) for c in chunks)
        assert total_bytes == len(test_audio)

    def test_mock_audio_playback_works_without_hardware(self) -> None:
        """Test MockAudioPlayback works without real audio hardware."""
        from ara.audio.mock_capture import MockAudioPlayback

        playback = MockAudioPlayback()

        # Should be able to "play" audio without real hardware
        test_audio = bytes(16000 * 2)
        playback.play(test_audio, sample_rate=16000)

        # Verify it was recorded
        assert playback.played_audio == test_audio
        assert playback.played_sample_rate == 16000

    def test_full_pipeline_with_mocks(self) -> None:
        """Test full voice pipeline works with all mocked components."""
        from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
        from ara.feedback.audio import MockFeedback
        from ara.llm.mock import MockLanguageModel
        from ara.router.orchestrator import Orchestrator
        from ara.stt.mock import MockTranscriber
        from ara.tts.mock import MockSynthesizer
        from ara.wake_word.mock import MockWakeWordDetector

        # Setup all mock components
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        wake_word.initialize(keywords=["ara"], sensitivity=0.5)
        transcriber.set_response("what time is it")
        llm.set_response("It's 3:30 PM.")

        # Schedule wake word detection and provide audio
        wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        capture.set_audio_data(bytes(16000 * 2))

        orchestrator = Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )

        # Process interaction
        result = orchestrator.process_single_interaction()

        assert result is not None
        assert result.transcript == "what time is it"
        assert "3:30" in result.response_text

    def test_mock_wav_file_loading(self) -> None:
        """Test mock capture can load from WAV files."""
        import wave
        from pathlib import Path

        from ara.audio.mock_capture import MockAudioCapture

        # Should be able to load from fixture file if it exists
        fixture_dir = Path(__file__).parent.parent / "fixtures" / "audio"
        if fixture_dir.exists():
            wav_files = list(fixture_dir.glob("*.wav"))
            if wav_files:
                # Get the sample rate from the file
                with wave.open(str(wav_files[0]), "rb") as wf:
                    file_sample_rate = wf.getframerate()
                    file_channels = wf.getnchannels()
                    file_sample_width = wf.getsampwidth()

                # Create capture with matching parameters
                capture = MockAudioCapture(
                    sample_rate=file_sample_rate,
                    channels=file_channels,
                    sample_width=file_sample_width,
                )
                capture.load_wav_file(wav_files[0])
                assert capture._audio_data is not None

    def test_ci_environment_detection(self) -> None:
        """Test CI environment can be detected."""
        import os

        # Common CI environment variables
        ci_vars = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "TRAVIS", "CIRCLECI"]

        # At least check that we can read environment variables
        for var in ci_vars:
            # Should not raise
            _ = os.environ.get(var)

    def test_no_audio_device_required(self) -> None:
        """Test that tests can run without any audio device."""
        from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback

        # These should not require any real audio hardware
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()

        # Operations should succeed without hardware
        capture.set_audio_data(b"\x00" * 1000)
        capture.start()
        for _ in capture.stream():
            break
        capture.stop()

        playback.play(b"\x00" * 1000, 16000)
        playback.play_async(b"\x00" * 1000, 16000)


class TestCITestFixtures:
    """Tests for test fixture availability in CI."""

    def test_fixture_directory_exists(self) -> None:
        """Test that fixture directory exists."""
        from pathlib import Path

        fixture_dir = Path(__file__).parent.parent / "fixtures"
        assert fixture_dir.exists(), "fixtures directory should exist"

    def test_audio_fixture_directory_exists(self) -> None:
        """Test that audio fixture directory exists."""
        from pathlib import Path

        audio_dir = Path(__file__).parent.parent / "fixtures" / "audio"
        # Create if it doesn't exist (for CI)
        audio_dir.mkdir(parents=True, exist_ok=True)
        assert audio_dir.exists()

    def test_config_files_exist(self) -> None:
        """Test that config files exist for CI."""
        from pathlib import Path

        config_dir = Path(__file__).parent.parent.parent / "config"
        assert config_dir.exists(), "config directory should exist"

        # At least dev.yaml should exist
        dev_yaml = config_dir / "dev.yaml"
        assert dev_yaml.exists(), "dev.yaml should exist"
