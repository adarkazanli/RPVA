"""Unit tests for platform detection."""

from unittest.mock import patch

import pytest

from ara.tts.platform import Platform, detect_platform


class TestPlatformEnum:
    """Test Platform enum values."""

    def test_platform_enum_has_macos(self) -> None:
        """Platform enum should have MACOS value."""
        assert hasattr(Platform, "MACOS")

    def test_platform_enum_has_raspberry_pi(self) -> None:
        """Platform enum should have RASPBERRY_PI value."""
        assert hasattr(Platform, "RASPBERRY_PI")

    def test_platform_enum_has_other(self) -> None:
        """Platform enum should have OTHER value."""
        assert hasattr(Platform, "OTHER")

    def test_platform_values_are_distinct(self) -> None:
        """All Platform enum values should be distinct."""
        values = [Platform.MACOS, Platform.RASPBERRY_PI, Platform.OTHER]
        assert len(values) == len(set(values))


class TestDetectPlatform:
    """Test detect_platform function."""

    def test_detect_macos_on_darwin(self) -> None:
        """Should return MACOS on Darwin (macOS)."""
        with (
            patch("ara.tts.platform.platform_module.system", return_value="Darwin"),
            patch("ara.tts.platform.platform_module.machine", return_value="arm64"),
        ):
            result = detect_platform()
            assert result == Platform.MACOS

    def test_detect_macos_on_intel_mac(self) -> None:
        """Should return MACOS on Intel Mac."""
        with (
            patch("ara.tts.platform.platform_module.system", return_value="Darwin"),
            patch("ara.tts.platform.platform_module.machine", return_value="x86_64"),
        ):
            result = detect_platform()
            assert result == Platform.MACOS

    def test_detect_raspberry_pi_aarch64(self) -> None:
        """Should return RASPBERRY_PI on Linux aarch64."""
        with (
            patch("ara.tts.platform.platform_module.system", return_value="Linux"),
            patch("ara.tts.platform.platform_module.machine", return_value="aarch64"),
        ):
            result = detect_platform()
            assert result == Platform.RASPBERRY_PI

    def test_detect_raspberry_pi_armv7l(self) -> None:
        """Should return RASPBERRY_PI on Linux armv7l."""
        with (
            patch("ara.tts.platform.platform_module.system", return_value="Linux"),
            patch("ara.tts.platform.platform_module.machine", return_value="armv7l"),
        ):
            result = detect_platform()
            assert result == Platform.RASPBERRY_PI

    def test_detect_other_on_linux_x86(self) -> None:
        """Should return OTHER on Linux x86_64."""
        with (
            patch("ara.tts.platform.platform_module.system", return_value="Linux"),
            patch("ara.tts.platform.platform_module.machine", return_value="x86_64"),
        ):
            result = detect_platform()
            assert result == Platform.OTHER

    def test_detect_other_on_windows(self) -> None:
        """Should return OTHER on Windows."""
        with (
            patch("ara.tts.platform.platform_module.system", return_value="Windows"),
            patch("ara.tts.platform.platform_module.machine", return_value="AMD64"),
        ):
            result = detect_platform()
            assert result == Platform.OTHER

    def test_detect_never_raises(self) -> None:
        """detect_platform should never raise exceptions."""
        # Test with unusual values that might cause issues
        test_cases = [
            ("", ""),
            ("Unknown", "unknown"),
            ("DARWIN", "ARM64"),  # Wrong case
        ]

        for system, machine in test_cases:
            with (
                patch("ara.tts.platform.platform_module.system", return_value=system),
                patch("ara.tts.platform.platform_module.machine", return_value=machine),
            ):
                # Should not raise
                result = detect_platform()
                assert isinstance(result, Platform)

    def test_returns_valid_platform_enum(self) -> None:
        """detect_platform should always return a valid Platform enum."""
        result = detect_platform()
        assert isinstance(result, Platform)
        assert result in list(Platform)
