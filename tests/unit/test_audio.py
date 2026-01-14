"""Unit tests for audio capture and playback."""

from unittest import mock

import pytest

from ara.audio import (
    AudioChunk,
    create_audio_capture,
    create_audio_playback,
    detect_audio_platform,
)
from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback


class TestAudioChunk:
    """Tests for AudioChunk dataclass."""

    def test_duration_calculation(self) -> None:
        """Test duration_ms property calculation."""
        # 1600 frames at 16000Hz = 100ms
        # 16-bit mono = 2 bytes per frame
        data = bytes(1600 * 2)
        chunk = AudioChunk(
            data=data,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp_ms=0,
        )
        assert chunk.duration_ms == pytest.approx(100.0)

    def test_num_frames(self) -> None:
        """Test num_frames property."""
        # 1024 frames * 2 bytes * 1 channel = 2048 bytes
        data = bytes(2048)
        chunk = AudioChunk(
            data=data,
            sample_rate=16000,
            channels=1,
            sample_width=2,
            timestamp_ms=0,
        )
        assert chunk.num_frames == 1024

    def test_stereo_frames(self) -> None:
        """Test frame calculation for stereo audio."""
        # 512 frames * 2 bytes * 2 channels = 2048 bytes
        data = bytes(2048)
        chunk = AudioChunk(
            data=data,
            sample_rate=16000,
            channels=2,
            sample_width=2,
            timestamp_ms=0,
        )
        assert chunk.num_frames == 512

    def test_zero_values_safety(self) -> None:
        """Test that zero values don't cause division errors."""
        chunk = AudioChunk(
            data=bytes(100),
            sample_rate=0,
            channels=0,
            sample_width=0,
            timestamp_ms=0,
        )
        assert chunk.duration_ms == 0.0
        assert chunk.num_frames == 0


class TestMockAudioCapture:
    """Tests for MockAudioCapture."""

    def test_start_stop(self) -> None:
        """Test starting and stopping capture."""
        capture = MockAudioCapture()
        assert capture.is_active is False

        capture.start()
        assert capture.is_active is True

        capture.stop()
        assert capture.is_active is False

    def test_read_silence(self) -> None:
        """Test reading silence when no audio source set."""
        capture = MockAudioCapture(sample_rate=16000)
        capture.start()

        chunk = capture.read(1024)

        assert len(chunk.data) == 1024 * 2  # 16-bit mono
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1
        assert all(b == 0 for b in chunk.data)  # All zeros (silence)

        capture.stop()

    def test_read_requires_active(self) -> None:
        """Test that reading requires active capture."""
        capture = MockAudioCapture()

        with pytest.raises(RuntimeError, match="not active"):
            capture.read(1024)

    def test_set_audio_data(self) -> None:
        """Test setting custom audio data."""
        capture = MockAudioCapture()

        # Set 100 frames of data (200 bytes for 16-bit mono)
        test_data = bytes(range(200))
        capture.set_audio_data(test_data)
        capture.start()

        chunk = capture.read(50)
        assert chunk.data == test_data[:100]  # First 50 frames

        chunk = capture.read(50)
        assert chunk.data == test_data[100:]  # Next 50 frames

        capture.stop()

    def test_stream_yields_chunks(self) -> None:
        """Test streaming mode yields chunks."""
        capture = MockAudioCapture(chunk_size=512)
        capture.set_audio_data(bytes(1024 * 2))  # 1024 frames of data

        chunks = []
        for chunk in capture.stream():
            chunks.append(chunk)
            if len(chunks) >= 2:
                break

        assert len(chunks) == 2
        assert all(c.num_frames == 512 for c in chunks)

    def test_has_audio_remaining(self) -> None:
        """Test has_audio_remaining property."""
        capture = MockAudioCapture()

        # No source = infinite
        assert capture.has_audio_remaining is True

        # With source
        capture.set_audio_data(bytes(100))
        capture.start()
        assert capture.has_audio_remaining is True

        capture.read(50)  # Read all
        assert capture.has_audio_remaining is False

        capture.stop()


class TestMockAudioPlayback:
    """Tests for MockAudioPlayback."""

    def test_play_records_audio(self) -> None:
        """Test that play records audio data."""
        playback = MockAudioPlayback()

        audio_data = bytes(range(100))
        playback.play(audio_data, 22050)

        assert playback.play_count == 1
        assert len(playback.all_played_audio) == 1
        assert playback.all_played_audio[0] == (audio_data, 22050)
        # Convenience properties return just the last played audio
        assert playback.played_audio == audio_data
        assert playback.played_sample_rate == 22050

    def test_play_async(self) -> None:
        """Test async playback."""
        playback = MockAudioPlayback()

        playback.play_async(bytes(100), 22050)

        assert playback.play_count == 1
        assert playback.is_playing is True

    def test_stop(self) -> None:
        """Test stopping playback."""
        playback = MockAudioPlayback()
        playback.play_async(bytes(100), 22050)

        playback.stop()

        assert playback.is_playing is False

    def test_play_tone(self) -> None:
        """Test playing a tone records data."""
        playback = MockAudioPlayback(sample_rate=22050)

        playback.play_tone(440, 100)

        assert playback.play_count == 1

    def test_clear(self) -> None:
        """Test clearing recorded audio."""
        playback = MockAudioPlayback()
        playback.play(bytes(100), 22050)
        playback.play(bytes(200), 22050)

        assert playback.play_count == 2

        playback.clear()

        assert playback.play_count == 0
        assert len(playback.all_played_audio) == 0
        assert playback.played_audio is None


class TestPlatformDetection:
    """Tests for platform detection."""

    def test_detect_macos(self) -> None:
        """Test macOS detection."""
        with mock.patch("platform.system", return_value="Darwin"):
            assert detect_audio_platform() == "macos"

    def test_detect_linux(self) -> None:
        """Test Linux detection."""
        with (
            mock.patch("platform.system", return_value="Linux"),
            mock.patch(
                "builtins.open",
                mock.mock_open(read_data="processor: 0\n"),
            ),
        ):
            assert detect_audio_platform() == "linux"

    def test_detect_raspberry_pi(self) -> None:
        """Test Raspberry Pi detection."""
        with (
            mock.patch("platform.system", return_value="Linux"),
            mock.patch(
                "builtins.open",
                mock.mock_open(read_data="Raspberry Pi 4 Model B\n"),
            ),
        ):
            assert detect_audio_platform() == "raspberrypi"


class TestFactoryFunctions:
    """Tests for audio factory functions."""

    def test_create_capture_mock(self) -> None:
        """Test creating mock capture."""
        capture = create_audio_capture(use_mock=True)
        assert isinstance(capture, MockAudioCapture)

    def test_create_playback_mock(self) -> None:
        """Test creating mock playback."""
        playback = create_audio_playback(use_mock=True)
        assert isinstance(playback, MockAudioPlayback)

    def test_create_capture_with_config(self) -> None:
        """Test creating capture with config."""
        from ara.config import AudioConfig

        config = AudioConfig(
            sample_rate=44100,
            channels=2,
            chunk_size=2048,
        )

        capture = create_audio_capture(config=config, use_mock=True)

        assert capture.sample_rate == 44100
        assert capture.channels == 2
