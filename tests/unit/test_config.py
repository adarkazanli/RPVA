"""Unit tests for configuration loading and profile management."""

import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import yaml

from ara.config import AraConfig
from ara.config.loader import (
    YAMLConfigLoader,
    deep_merge,
    dict_to_config,
    load_config,
    load_yaml_with_inheritance,
)
from ara.config.profiles import (
    Platform,
    Profile,
    detect_platform,
    detect_profile,
    get_profile_path,
    is_development,
    is_production,
)


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_simple_merge(self) -> None:
        """Test merging flat dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self) -> None:
        """Test merging nested dictionaries."""
        base = {"outer": {"a": 1, "b": 2}}
        override = {"outer": {"b": 3, "c": 4}}
        result = deep_merge(base, override)
        assert result == {"outer": {"a": 1, "b": 3, "c": 4}}

    def test_deep_nested_merge(self) -> None:
        """Test deeply nested merge."""
        base = {"l1": {"l2": {"l3": {"a": 1}}}}
        override = {"l1": {"l2": {"l3": {"b": 2}}}}
        result = deep_merge(base, override)
        assert result == {"l1": {"l2": {"l3": {"a": 1, "b": 2}}}}

    def test_override_replaces_non_dict(self) -> None:
        """Test that non-dict values are replaced."""
        base = {"a": {"nested": 1}}
        override = {"a": "replaced"}
        result = deep_merge(base, override)
        assert result == {"a": "replaced"}


class TestYAMLLoading:
    """Tests for YAML config loading."""

    def test_load_simple_yaml(self) -> None:
        """Test loading a simple YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"ara": {"wake_word": {"keyword": "test"}}}, f)
            f.flush()

            result = load_yaml_with_inheritance(Path(f.name))
            assert result["ara"]["wake_word"]["keyword"] == "test"

        os.unlink(f.name)

    def test_load_with_inheritance(self) -> None:
        """Test loading YAML with extends keyword."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create base config
            base_path = Path(tmpdir) / "base.yaml"
            with open(base_path, "w") as f:
                yaml.dump(
                    {
                        "ara": {
                            "wake_word": {"keyword": "base", "sensitivity": 0.5},
                            "stt": {"model": "base.en"},
                        }
                    },
                    f,
                )

            # Create child config that extends base
            child_path = Path(tmpdir) / "child.yaml"
            with open(child_path, "w") as f:
                yaml.dump(
                    {
                        "extends": "base.yaml",
                        "ara": {"wake_word": {"keyword": "child"}},
                    },
                    f,
                )

            result = load_yaml_with_inheritance(child_path)
            # Child overrides keyword
            assert result["ara"]["wake_word"]["keyword"] == "child"
            # Base sensitivity preserved
            assert result["ara"]["wake_word"]["sensitivity"] == 0.5
            # Base stt preserved
            assert result["ara"]["stt"]["model"] == "base.en"

    def test_file_not_found(self) -> None:
        """Test FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError):
            load_yaml_with_inheritance(Path("/nonexistent/config.yaml"))


class TestDictToConfig:
    """Tests for converting dict to AraConfig."""

    def test_empty_dict(self) -> None:
        """Test conversion of empty dict uses defaults."""
        config = dict_to_config({})
        assert config.wake_word.keyword == "ara"
        assert config.stt.model == "base.en"
        assert config.llm.provider == "ollama"

    def test_partial_override(self) -> None:
        """Test partial config override."""
        data = {"ara": {"wake_word": {"keyword": "custom"}}}
        config = dict_to_config(data)
        assert config.wake_word.keyword == "custom"
        assert config.wake_word.sensitivity == 0.5  # Default preserved


class TestYAMLConfigLoader:
    """Tests for YAMLConfigLoader class."""

    def test_load_dev_profile(self) -> None:
        """Test loading dev profile from actual config directory."""
        # Use the actual project config directory
        config_dir = Path(__file__).parent.parent.parent / "config"
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        loader = YAMLConfigLoader(config_dir)
        config = loader.load_profile("dev")

        assert isinstance(config, AraConfig)
        assert config.logging.level == "DEBUG"

    def test_load_prod_profile(self) -> None:
        """Test loading prod profile from actual config directory."""
        config_dir = Path(__file__).parent.parent.parent / "config"
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        loader = YAMLConfigLoader(config_dir)
        config = loader.load_profile("prod")

        assert isinstance(config, AraConfig)
        assert config.logging.level == "INFO"
        assert config.stt.compute_type == "int8"

    def test_get_config_dir(self) -> None:
        """Test get_config_dir returns correct path."""
        custom_dir = Path("/custom/config")
        loader = YAMLConfigLoader(custom_dir)
        assert loader.get_config_dir() == custom_dir


class TestLoadConfigFunction:
    """Tests for convenience load_config function."""

    def test_load_by_profile(self) -> None:
        """Test loading config by profile name."""
        config_dir = Path(__file__).parent.parent.parent / "config"
        if not config_dir.exists():
            pytest.skip("Config directory not found")

        config = load_config(profile="dev")
        assert isinstance(config, AraConfig)


class TestProfileDetection:
    """Tests for profile detection."""

    def test_detect_profile_from_env(self) -> None:
        """Test profile detection from environment variable."""
        with mock.patch.dict(os.environ, {"ARA_PROFILE": "prod"}):
            assert detect_profile() == Profile.PROD

        with mock.patch.dict(os.environ, {"ARA_PROFILE": "dev"}):
            assert detect_profile() == Profile.DEV

    def test_detect_profile_default_dev(self) -> None:
        """Test default profile is dev on non-Pi systems."""
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "ara.config.profiles.detect_platform",
            return_value=Platform.MACOS,
        ):
            assert detect_profile() == Profile.DEV

    def test_detect_profile_pi_is_prod(self) -> None:
        """Test Raspberry Pi defaults to prod profile."""
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch(
            "ara.config.profiles.detect_platform",
            return_value=Platform.RASPBERRY_PI,
        ):
            assert detect_profile() == Profile.PROD


class TestPlatformDetection:
    """Tests for platform detection."""

    def test_detect_macos(self) -> None:
        """Test macOS detection."""
        with mock.patch("platform.system", return_value="Darwin"):
            assert detect_platform() == Platform.MACOS

    def test_detect_linux(self) -> None:
        """Test Linux detection."""
        with mock.patch("platform.system", return_value="Linux"), mock.patch(
            "builtins.open",
            mock.mock_open(read_data="processor: 0\n"),
        ):
            assert detect_platform() == Platform.LINUX

    def test_is_development(self) -> None:
        """Test is_development helper."""
        with mock.patch(
            "ara.config.profiles.detect_profile",
            return_value=Profile.DEV,
        ):
            assert is_development() is True
            assert is_production() is False

    def test_is_production(self) -> None:
        """Test is_production helper."""
        with mock.patch(
            "ara.config.profiles.detect_profile",
            return_value=Profile.PROD,
        ):
            assert is_production() is True
            assert is_development() is False


class TestGetProfilePath:
    """Tests for get_profile_path function."""

    def test_explicit_profile(self) -> None:
        """Test getting path for explicit profile."""
        path = get_profile_path(Profile.DEV, Path("/config"))
        assert path == Path("/config/dev.yaml")

    def test_auto_detect_profile(self) -> None:
        """Test auto-detecting profile for path."""
        with mock.patch(
            "ara.config.profiles.detect_profile",
            return_value=Profile.PROD,
        ):
            path = get_profile_path(config_dir=Path("/config"))
            assert path == Path("/config/prod.yaml")
