"""macOS audio backend using PyAudio.

Provides AudioCapture and AudioPlayback implementations for macOS
using PyAudio (PortAudio wrapper).
"""

import math
import struct
import threading
import time
from collections.abc import Iterator
from typing import Any

from ..capture import AudioChunk

# PyAudio import with fallback for type hints
try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None


class MacOSAudioCapture:
    """macOS audio capture using PyAudio.

    Implements the AudioCapture protocol for macOS systems.
    """

    def __init__(
        self,
        device_name: str = "default",
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
    ) -> None:
        """Initialize macOS audio capture.

        Args:
            device_name: Audio input device name or "default"
            sample_rate: Sample rate in Hz
            channels: Number of channels (1 for mono)
            chunk_size: Frames per buffer

        Raises:
            RuntimeError: If PyAudio is not available
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available. Install with: pip install pyaudio")

        self._device_name = device_name
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_size = chunk_size
        self._sample_width = 2  # 16-bit audio

        self._pa: Any = None
        self._stream: Any = None
        self._is_active = False
        self._start_time_ms = 0

    def _get_device_index(self) -> int | None:
        """Get device index for configured device name."""
        if self._device_name == "default":
            return None  # Use default device

        if self._pa is None:
            return None

        for i in range(self._pa.get_device_count()):
            info = self._pa.get_device_info_by_index(i)
            if self._device_name.lower() in info["name"].lower() and info["maxInputChannels"] > 0:
                return i

        return None  # Fall back to default

    def start(self) -> None:
        """Start audio capture."""
        if self._is_active:
            return

        self._pa = pyaudio.PyAudio()
        device_index = self._get_device_index()

        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self._channels,
            rate=self._sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self._chunk_size,
        )

        self._is_active = True
        self._start_time_ms = int(time.time() * 1000)

    def stop(self) -> None:
        """Stop audio capture."""
        if not self._is_active:
            return

        self._is_active = False

        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pa is not None:
            self._pa.terminate()
            self._pa = None

    def read(self, frames: int) -> AudioChunk:
        """Read audio frames from input."""
        if not self._is_active or self._stream is None:
            raise RuntimeError("Capture not active")

        data = self._stream.read(frames, exception_on_overflow=False)
        timestamp = int(time.time() * 1000) - self._start_time_ms

        return AudioChunk(
            data=data,
            sample_rate=self._sample_rate,
            channels=self._channels,
            sample_width=self._sample_width,
            timestamp_ms=timestamp,
        )

    def stream(self) -> Iterator[AudioChunk]:
        """Yield audio chunks continuously."""
        if not self._is_active:
            self.start()

        while self._is_active:
            yield self.read(self._chunk_size)

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

    def __enter__(self) -> "MacOSAudioCapture":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.stop()


class MacOSAudioPlayback:
    """macOS audio playback using PyAudio.

    Implements the AudioPlayback protocol for macOS systems.
    """

    def __init__(
        self,
        device_name: str = "default",
        sample_rate: int = 22050,
    ) -> None:
        """Initialize macOS audio playback.

        Args:
            device_name: Audio output device name or "default"
            sample_rate: Default output sample rate in Hz

        Raises:
            RuntimeError: If PyAudio is not available
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio not available. Install with: pip install pyaudio")

        self._device_name = device_name
        self._sample_rate = sample_rate
        self._is_playing = False
        self._stop_flag = threading.Event()
        self._play_thread: threading.Thread | None = None

    def _get_device_index(self, pa: Any) -> int | None:
        """Get device index for configured device name."""
        if self._device_name == "default":
            return None

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if self._device_name.lower() in info["name"].lower() and info["maxOutputChannels"] > 0:
                return i

        return None

    def play(self, audio: bytes, sample_rate: int) -> None:
        """Play audio synchronously."""
        self._is_playing = True
        self._stop_flag.clear()

        pa = pyaudio.PyAudio()
        try:
            device_index = self._get_device_index(pa)
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
                output_device_index=device_index,
            )

            try:
                chunk_size = 1024
                for i in range(0, len(audio), chunk_size * 2):
                    if self._stop_flag.is_set():
                        break
                    chunk = audio[i : i + chunk_size * 2]
                    stream.write(chunk)
            finally:
                stream.stop_stream()
                stream.close()
        finally:
            pa.terminate()
            self._is_playing = False

    def play_async(self, audio: bytes, sample_rate: int) -> None:
        """Play audio asynchronously in background thread."""
        self._stop_flag.clear()
        self._play_thread = threading.Thread(
            target=self.play,
            args=(audio, sample_rate),
            daemon=True,
        )
        self._play_thread.start()

    def stop(self) -> None:
        """Stop current playback."""
        self._stop_flag.set()
        if self._play_thread is not None:
            self._play_thread.join(timeout=1.0)
            self._play_thread = None
        self._is_playing = False

    def play_tone(self, frequency: int, duration_ms: int) -> None:
        """Play a simple sine wave tone."""
        num_samples = int(self._sample_rate * duration_ms / 1000)
        audio_data = []

        for i in range(num_samples):
            t = i / self._sample_rate
            sample = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
            audio_data.append(struct.pack("<h", sample))

        self.play(b"".join(audio_data), self._sample_rate)

    @property
    def is_playing(self) -> bool:
        """Return True if audio is playing."""
        return self._is_playing

    @property
    def sample_rate(self) -> int:
        """Get output sample rate."""
        return self._sample_rate


__all__ = ["MacOSAudioCapture", "MacOSAudioPlayback"]
