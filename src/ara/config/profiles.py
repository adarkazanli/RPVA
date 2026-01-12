"""Configuration profile management.

Provides utilities for detecting and managing configuration profiles
based on environment and platform.
"""

import os
import platform
from enum import Enum
from pathlib import Path


class Profile(Enum):
    """Available configuration profiles."""

    DEV = "dev"
    PROD = "prod"
    TEST = "test"


class Platform(Enum):
    """Supported platforms."""

    MACOS = "macos"
    LINUX = "linux"
    RASPBERRY_PI = "raspberrypi"
    UNKNOWN = "unknown"


def detect_platform() -> Platform:
    """Detect the current platform.

    Returns:
        Platform enum value
    """
    system = platform.system().lower()

    if system == "darwin":
        return Platform.MACOS
    elif system == "linux":
        # Check for Raspberry Pi
        try:
            with open("/proc/cpuinfo") as f:
                if "Raspberry Pi" in f.read():
                    return Platform.RASPBERRY_PI
        except (FileNotFoundError, PermissionError):
            pass
        return Platform.LINUX
    else:
        return Platform.UNKNOWN


def detect_profile() -> Profile:
    """Detect appropriate configuration profile.

    Checks in order:
    1. ARA_PROFILE environment variable
    2. Platform detection (Raspberry Pi = prod, else dev)

    Returns:
        Profile enum value
    """
    # Check environment variable first
    env_profile = os.environ.get("ARA_PROFILE", "").lower()
    if env_profile == "prod":
        return Profile.PROD
    elif env_profile == "dev":
        return Profile.DEV
    elif env_profile == "test":
        return Profile.TEST

    # Auto-detect based on platform
    plat = detect_platform()
    if plat == Platform.RASPBERRY_PI:
        return Profile.PROD
    else:
        return Profile.DEV


def get_profile_path(profile: Profile | None = None, config_dir: Path | None = None) -> Path:
    """Get path to profile configuration file.

    Args:
        profile: Profile to use, or None to auto-detect
        config_dir: Configuration directory, or None for default

    Returns:
        Path to profile YAML file
    """
    if profile is None:
        profile = detect_profile()

    if config_dir is None:
        # Default: config/ relative to project root
        config_dir = Path(__file__).parent.parent.parent.parent / "config"

    return config_dir / f"{profile.value}.yaml"


def is_development() -> bool:
    """Check if running in development mode."""
    return detect_profile() == Profile.DEV


def is_production() -> bool:
    """Check if running in production mode."""
    return detect_profile() == Profile.PROD


def is_raspberry_pi() -> bool:
    """Check if running on Raspberry Pi."""
    return detect_platform() == Platform.RASPBERRY_PI


def is_macos() -> bool:
    """Check if running on macOS."""
    return detect_platform() == Platform.MACOS


def is_linux() -> bool:
    """Check if running on Linux (non-Pi)."""
    return detect_platform() == Platform.LINUX


__all__ = [
    "Platform",
    "Profile",
    "detect_platform",
    "detect_profile",
    "get_profile_path",
    "is_development",
    "is_linux",
    "is_macos",
    "is_production",
    "is_raspberry_pi",
]
