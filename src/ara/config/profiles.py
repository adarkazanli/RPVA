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


class Accelerator(Enum):
    """Available hardware accelerators for ML inference."""

    METAL = "metal"  # Apple Silicon GPU
    CUDA = "cuda"  # NVIDIA GPU
    CPU = "cpu"  # CPU only


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


def detect_accelerator() -> Accelerator:
    """Detect available hardware accelerator for ML inference.

    Checks for:
    1. Apple Metal (macOS with Apple Silicon)
    2. NVIDIA CUDA
    3. Falls back to CPU

    Returns:
        Accelerator enum value
    """
    # Check for Apple Metal (macOS)
    if platform.system() == "Darwin":
        # Check if running on Apple Silicon
        try:
            import subprocess

            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "Apple" in result.stdout:
                return Accelerator.METAL
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        # Check for Metal support via torch (if available)
        try:
            import torch

            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return Accelerator.METAL
        except ImportError:
            pass

    # Check for CUDA
    try:
        import torch

        if torch.cuda.is_available():
            return Accelerator.CUDA
    except ImportError:
        pass

    # Check for CUDA without torch
    try:
        import subprocess

        nvidia_result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            timeout=5,
        )
        if nvidia_result.returncode == 0:
            return Accelerator.CUDA
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return Accelerator.CPU


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
    profile_map = {
        "prod": Profile.PROD,
        "dev": Profile.DEV,
        "test": Profile.TEST,
    }
    if env_profile in profile_map:
        return profile_map[env_profile]

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
    "Accelerator",
    "Platform",
    "Profile",
    "detect_accelerator",
    "detect_platform",
    "detect_profile",
    "get_profile_path",
    "is_development",
    "is_linux",
    "is_macos",
    "is_production",
    "is_raspberry_pi",
]
