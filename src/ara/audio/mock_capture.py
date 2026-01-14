"""Mock audio capture for testing.

Provides a mock implementation of AudioCapture that can be used for
testing without requiring actual audio hardware.
"""

import time
import wave
from collections.abc import Iterator
from pathlib import Path

from .capture import AudioChunk


class MockAudioCapture:
    """Mock audio capture for testing.

    Can simulate audio capture from:
    - Silence (generates empty audio chunks)
    - WAV files (plays back pre-recorded audio)
    - Custom audio data (for programmatic testing)

    Implements the AudioCapture protocol.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
        chunk_size: int = 1024,
    ) -> None:
        """Initialize mock capture.

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            sample_width: Bytes per sample
            chunk_size: Frames per chunk when streaming
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._sample_width = sample_width
        self._chunk_size = chunk_size
        self._is_active = False
        self._audio_source: bytes | None = None
        self._source_position = 0
        self._start_time_ms = 0

    def set_audio_file(self, path: Path | str) -> None:
        """Load audio from a WAV file.

        Args:
            path: Path to WAV file

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format doesn't match configuration
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {path}")

        with wave.open(str(path), "rb") as wf:
            if wf.getsampwidth() != self._sample_width:
                raise ValueError(
                    f"Sample width mismatch: file={wf.getsampwidth()}, "
                    f"expected={self._sample_width}"
                )
            if wf.getnchannels() != self._channels:
                raise ValueError(
                    f"Channel count mismatch: file={wf.getnchannels()}, expected={self._channels}"
                )
            if wf.getframerate() != self._sample_rate:
                raise ValueError(
                    f"Sample rate mismatch: file={wf.getframerate()}, expected={self._sample_rate}"
                )
            self._audio_source = wf.readframes(wf.getnframes())
            self._source_position = 0

    def set_audio_data(self, data: bytes) -> None:
        """Set raw audio data for playback.

        Args:
            data: Raw PCM audio bytes
        """
        self._audio_source = data
        self._source_position = 0

    def start(self) -> None:
        """Start mock capture."""
        self._is_active = True
        self._source_position = 0
        self._start_time_ms = int(time.time() * 1000)

    def stop(self) -> None:
        """Stop mock capture."""
        self._is_active = False

    def read(self, frames: int) -> AudioChunk:
        """Read audio frames.

        If audio source is set, reads from it. Otherwise generates silence.

        Args:
            frames: Number of frames to read

        Returns:
            AudioChunk with requested frames
        """
        if not self._is_active:
            raise RuntimeError("Capture not active")

        bytes_needed = frames * self._sample_width * self._channels
        timestamp = int(time.time() * 1000) - self._start_time_ms

        if self._audio_source is not None:
            # Read from audio source
            available = len(self._audio_source) - self._source_position
            bytes_to_read = min(bytes_needed, available)

            if bytes_to_read > 0:
                data = self._audio_source[
                    self._source_position : self._source_position + bytes_to_read
                ]
                self._source_position += bytes_to_read
            else:
                # Source exhausted, return silence
                data = bytes(bytes_needed)
        else:
            # No source, generate silence
            data = bytes(bytes_needed)

        return AudioChunk(
            data=data,
            sample_rate=self._sample_rate,
            channels=self._channels,
            sample_width=self._sample_width,
            timestamp_ms=timestamp,
        )

    def stream(self) -> Iterator[AudioChunk]:
        """Yield audio chunks continuously.

        Yields chunks at approximately real-time rate based on sample rate.
        """
        if not self._is_active:
            self.start()

        chunk_duration_sec = self._chunk_size / self._sample_rate

        while self._is_active:
            chunk = self.read(self._chunk_size)
            yield chunk

            # If we have a source and it's exhausted, stop
            if self._audio_source is not None and self._source_position >= len(self._audio_source):
                break

            # Simulate real-time by sleeping
            time.sleep(chunk_duration_sec * 0.9)  # Slightly faster to avoid buffer underrun

    @property
    def is_active(self) -> bool:
        """Return True if capture is active."""
        return self._is_active

    @property
    def sample_rate(self) -> int:
        """Get sample rate."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Get channel count."""
        return self._channels

    @property
    def sample_width(self) -> int:
        """Get sample width."""
        return self._sample_width

    @property
    def has_audio_remaining(self) -> bool:
        """Check if there's audio remaining in the source."""
        if self._audio_source is None:
            return True  # Infinite silence
        return self._source_position < len(self._audio_source)

    @property
    def _audio_data(self) -> bytes | None:
        """Get raw audio data (for testing)."""
        return self._audio_source

    def load_wav_file(self, path: Path | str) -> None:
        """Alias for set_audio_file (for compatibility).

        Args:
            path: Path to WAV file
        """
        self.set_audio_file(path)


class MockAudioPlayback:
    """Mock audio playback for testing.

    Records all audio that would be played for later verification.
    Implements the AudioPlayback protocol.
    """

    def __init__(self, sample_rate: int = 22050) -> None:
        """Initialize mock playback.

        Args:
            sample_rate: Output sample rate in Hz
        """
        self._sample_rate = sample_rate
        self._is_playing = False
        self._played_audio: list[tuple[bytes, int]] = []  # (audio, sample_rate) pairs
        self._play_count = 0

    def play(self, audio: bytes, sample_rate: int) -> None:
        """Record audio that would be played (synchronous)."""
        self._played_audio.append((audio, sample_rate))
        self._play_count += 1
        # Simulate playback time
        duration_sec = len(audio) / (sample_rate * 2)  # Assuming 16-bit mono
        time.sleep(min(duration_sec * 0.1, 0.1))  # Cap at 100ms for tests

    def play_async(self, audio: bytes, sample_rate: int) -> None:
        """Record audio that would be played (async)."""
        self._played_audio.append((audio, sample_rate))
        self._play_count += 1
        self._is_playing = True

    def stop(self) -> None:
        """Stop mock playback."""
        self._is_playing = False

    def play_tone(self, _frequency: int, duration_ms: int) -> None:
        """Record tone that would be played."""
        # Generate a simple tone representation (frequency ignored in mock)
        num_samples = int(self._sample_rate * duration_ms / 1000)
        # Just store placeholder data indicating a tone was requested
        self._played_audio.append((bytes(num_samples * 2), self._sample_rate))
        self._play_count += 1

    @property
    def is_playing(self) -> bool:
        """Return True if 'playing'."""
        return self._is_playing

    @property
    def sample_rate(self) -> int:
        """Get output sample rate."""
        return self._sample_rate

    @property
    def play_count(self) -> int:
        """Get number of times play was called."""
        return self._play_count

    @property
    def played_audio(self) -> bytes | None:
        """Get the last played audio bytes (convenience property)."""
        if not self._played_audio:
            return None
        return self._played_audio[-1][0]

    @property
    def played_sample_rate(self) -> int | None:
        """Get the sample rate of the last played audio."""
        if not self._played_audio:
            return None
        return self._played_audio[-1][1]

    @property
    def all_played_audio(self) -> list[tuple[bytes, int]]:
        """Get list of all (audio, sample_rate) pairs that were played."""
        return self._played_audio.copy()

    def clear(self) -> None:
        """Clear recorded audio."""
        self._played_audio.clear()
        self._play_count = 0


__all__ = ["MockAudioCapture", "MockAudioPlayback"]
