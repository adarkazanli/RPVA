"""Audio module for Ara Voice Assistant.

Provides platform-independent audio capture and playback with automatic
platform detection and appropriate backend selection.

Usage:
    # Get platform-appropriate audio capture
    capture = create_audio_capture(config.audio)

    # Get platform-appropriate audio playback
    playback = create_audio_playback(config.audio)

    # For testing, use mock implementations
    from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
"""

import platform
from typing import TYPE_CHECKING

from .capture import AudioCapture, AudioChunk
from .playback import AudioPlayback

if TYPE_CHECKING:
    from ..config import AudioConfig


def detect_audio_platform() -> str:
    """Detect the current platform for audio backend selection.

    Returns:
        Platform identifier: "macos", "linux", "raspberrypi", or "unknown"
    """
    system = platform.system().lower()

    if system == "darwin":
        return "macos"
    elif system == "linux":
        # Check for Raspberry Pi
        try:
            with open("/proc/cpuinfo") as f:
                if "Raspberry Pi" in f.read():
                    return "raspberrypi"
        except (FileNotFoundError, PermissionError):
            pass
        return "linux"
    else:
        return "unknown"


def create_audio_capture(
    config: "AudioConfig | None" = None,
    use_mock: bool = False,
) -> AudioCapture:
    """Create platform-appropriate audio capture instance.

    Args:
        config: Audio configuration (uses defaults if None)
        use_mock: If True, return mock implementation for testing

    Returns:
        AudioCapture implementation for current platform

    Raises:
        RuntimeError: If no suitable audio backend is available
    """
    # Default configuration values
    device_name = "default"
    sample_rate = 16000
    channels = 1
    chunk_size = 1024

    if config is not None:
        device_name = config.input_device
        sample_rate = config.sample_rate
        channels = config.channels
        chunk_size = config.chunk_size

    if use_mock:
        from .mock_capture import MockAudioCapture

        return MockAudioCapture(
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=chunk_size,
        )

    plat = detect_audio_platform()

    if plat == "macos":
        from .backends.macos import MacOSAudioCapture

        return MacOSAudioCapture(
            device_name=device_name,
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=chunk_size,
        )
    elif plat in ("linux", "raspberrypi"):
        from .backends.linux import LinuxAudioCapture

        return LinuxAudioCapture(
            device_name=device_name,
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=chunk_size,
        )
    else:
        raise RuntimeError(f"Unsupported platform for audio capture: {plat}")


def create_audio_playback(
    config: "AudioConfig | None" = None,
    use_mock: bool = False,
) -> AudioPlayback:
    """Create platform-appropriate audio playback instance.

    Args:
        config: Audio configuration (uses defaults if None)
        use_mock: If True, return mock implementation for testing

    Returns:
        AudioPlayback implementation for current platform

    Raises:
        RuntimeError: If no suitable audio backend is available
    """
    # Default values
    device_name = "default"
    sample_rate = 22050  # Common TTS output rate

    if config is not None:
        device_name = config.output_device

    if use_mock:
        from .mock_capture import MockAudioPlayback

        return MockAudioPlayback(sample_rate=sample_rate)

    plat = detect_audio_platform()

    if plat == "macos":
        from .backends.macos import MacOSAudioPlayback

        return MacOSAudioPlayback(
            device_name=device_name,
            sample_rate=sample_rate,
        )
    elif plat in ("linux", "raspberrypi"):
        from .backends.linux import LinuxAudioPlayback

        return LinuxAudioPlayback(
            device_name=device_name,
            sample_rate=sample_rate,
        )
    else:
        raise RuntimeError(f"Unsupported platform for audio playback: {plat}")


__all__ = [
    "AudioCapture",
    "AudioChunk",
    "AudioPlayback",
    "create_audio_capture",
    "create_audio_playback",
    "detect_audio_platform",
]
