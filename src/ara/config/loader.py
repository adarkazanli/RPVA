"""YAML configuration loader with inheritance support.

Supports:
- Loading YAML config files
- Config inheritance via 'extends' key
- Deep merging of nested config
"""

from pathlib import Path
from typing import Any

import yaml

from . import (
    AraConfig,
    AudioConfig,
    CloudConfig,
    DevConfig,
    FeedbackConfig,
    LLMConfig,
    LoggingConfig,
    ModeConfig,
    PerformanceConfig,
    ProductionConfig,
    STTConfig,
    TestingConfig,
    TTSConfig,
    WakeWordConfig,
)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Values from override take precedence. Nested dicts are merged recursively.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_yaml_with_inheritance(path: Path) -> dict[str, Any]:
    """Load YAML file with inheritance support.

    If the file contains an 'extends' key, the base config is loaded first
    and merged with the current config.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        config = yaml.safe_load(f) or {}

    # Handle inheritance
    if "extends" in config:
        base_name = config.pop("extends")
        base_path = path.parent / base_name
        base_config = load_yaml_with_inheritance(base_path)
        config = deep_merge(base_config, config)

    return config


def dict_to_config(data: dict[str, Any]) -> AraConfig:
    """Convert raw dict to typed AraConfig dataclass."""
    ara_data = data.get("ara", {}) or {}

    # Helper to safely get dict values (handles None from YAML)
    def safe_get(key: str) -> dict[str, Any]:
        value = ara_data.get(key, {})
        return value if value is not None else {}

    return AraConfig(
        wake_word=WakeWordConfig(**safe_get("wake_word")),
        audio=AudioConfig(**safe_get("audio")),
        stt=STTConfig(**safe_get("stt")),
        llm=LLMConfig(**safe_get("llm")),
        tts=TTSConfig(**safe_get("tts")),
        mode=ModeConfig(**safe_get("mode")),
        logging=LoggingConfig(**safe_get("logging")),
        feedback=_parse_feedback_config(safe_get("feedback")),
        performance=PerformanceConfig(**safe_get("performance")),
        cloud=CloudConfig(**safe_get("cloud")),
        testing=TestingConfig(**safe_get("testing")),
        dev=DevConfig(**safe_get("dev")),
        production=ProductionConfig(**safe_get("production")),
    )


def _parse_feedback_config(data: dict[str, Any]) -> FeedbackConfig:
    """Parse feedback config, handling nested sounds dict."""
    sounds = data.get("sounds", {})
    return FeedbackConfig(
        audio_enabled=data.get("audio_enabled", True),
        sounds=sounds,
    )


class YAMLConfigLoader:
    """YAML configuration loader implementation."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize loader with optional config directory.

        Args:
            config_dir: Directory containing config files.
                        Defaults to 'config' relative to project root.
        """
        if config_dir is None:
            # Default to config/ in project root
            config_dir = Path(__file__).parent.parent.parent.parent / "config"
        self._config_dir = config_dir

    def load(self, path: Path) -> AraConfig:
        """Load configuration from file path.

        Args:
            path: Path to YAML config file

        Returns:
            Parsed AraConfig
        """
        raw_config = load_yaml_with_inheritance(path)
        return dict_to_config(raw_config)

    def load_profile(self, profile: str) -> AraConfig:
        """Load configuration by profile name.

        Args:
            profile: Profile name (e.g., 'dev', 'prod')

        Returns:
            Parsed AraConfig for the profile
        """
        config_path = self._config_dir / f"{profile}.yaml"
        return self.load(config_path)

    def get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        return self._config_dir


# Convenience function
def load_config(path: str | Path | None = None, profile: str | None = None) -> AraConfig:
    """Load Ara configuration.

    Args:
        path: Direct path to config file (takes precedence)
        profile: Profile name ('dev', 'prod') if path not given

    Returns:
        Parsed AraConfig

    Examples:
        >>> config = load_config(profile="dev")
        >>> config = load_config(path="/path/to/config.yaml")
    """
    loader = YAMLConfigLoader()

    if path is not None:
        return loader.load(Path(path))
    elif profile is not None:
        return loader.load_profile(profile)
    else:
        # Default to dev profile
        return loader.load_profile("dev")


__all__ = [
    "YAMLConfigLoader",
    "deep_merge",
    "load_config",
    "load_yaml_with_inheritance",
]
