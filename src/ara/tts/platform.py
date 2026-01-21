"""Platform detection for TTS engine selection.

Detects the current platform to select the optimal TTS engine.
"""

import platform as platform_module
from enum import Enum, auto


class Platform(Enum):
    """Detected platform for TTS engine selection."""

    MACOS = auto()
    RASPBERRY_PI = auto()
    OTHER = auto()


def detect_platform() -> Platform:
    """Detect the current platform for TTS engine selection.

    Returns:
        Platform enum indicating the detected platform:
        - MACOS for Darwin systems (any architecture)
        - RASPBERRY_PI for Linux on ARM (aarch64, armv7l)
        - OTHER for all other platforms

    This function never raises exceptions.
    """
    system = platform_module.system()
    machine = platform_module.machine()

    if system == "Darwin":
        return Platform.MACOS
    elif system == "Linux" and machine in ("aarch64", "armv7l"):
        return Platform.RASPBERRY_PI
    else:
        return Platform.OTHER


__all__ = ["Platform", "detect_platform"]
