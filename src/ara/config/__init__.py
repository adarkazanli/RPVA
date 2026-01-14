"""Configuration module for Ara Voice Assistant.

This module provides configuration loading and profile management.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .user_profile import UserProfile, load_user_profile, save_user_profile


@dataclass
class WakeWordConfig:
    """Wake word detection configuration."""

    keyword: str = "ara"
    sensitivity: float = 0.5
    model_path: str | None = None


@dataclass
class AudioConfig:
    """Audio input/output configuration."""

    input_device: str = "default"
    output_device: str = "default"
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024


@dataclass
class STTConfig:
    """Speech-to-text configuration."""

    model: str = "base.en"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 1
    vad_filter: bool = True


@dataclass
class LLMConfig:
    """Language model configuration."""

    provider: str = "ollama"
    model: str = "llama3.2:3b"
    host: str = "http://localhost:11434"
    max_tokens: int = 150
    temperature: float = 0.7
    system_prompt: str = (
        "You are Ara, a helpful voice assistant. Keep responses brief, "
        "conversational, and under 2 sentences. Be natural and friendly. "
        "Never use markdown, lists, or formatting—speak naturally. "
        "If you don't know something, say so briefly."
    )


@dataclass
class TTSConfig:
    """Text-to-speech configuration."""

    voice: str = "en_US-lessac-medium"
    speed: float = 1.0
    model_path: str | None = None


@dataclass
class ModeConfig:
    """Operation mode configuration."""

    default: str = "offline"
    auto_detect_network: bool = True
    network_check_interval: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    enabled: bool = True
    format: str = "jsonl"
    retention_days: int = 90
    log_dir: str = "~/ara/logs"
    summary_dir: str = "~/ara/summaries"


@dataclass
class FeedbackConfig:
    """Audio feedback configuration."""

    audio_enabled: bool = True
    sounds: dict[str, str] = field(
        default_factory=lambda: {
            "wake_detected": "beep.wav",
            "error": "error.wav",
            "mode_change": "chime.wav",
            "timer_alert": "alarm.wav",
        }
    )


@dataclass
class PerformanceConfig:
    """Performance settings."""

    preload_models: bool = True
    latency_warning_ms: int = 3000


@dataclass
class CloudConfig:
    """Cloud service configuration."""

    claude_model: str = "claude-3-haiku-20240307"
    search_enabled: bool = True
    weather_enabled: bool = True


@dataclass
class TestingConfig:
    """Testing configuration."""

    mock_audio_enabled: bool = False
    mock_audio_dir: str = "tests/fixtures/audio"
    benchmark_mode: bool = False


@dataclass
class DevConfig:
    """Development configuration."""

    hot_reload: bool = False
    profile_latency: bool = True
    save_debug_audio: bool = False


@dataclass
class ProductionConfig:
    """Production-specific configuration."""

    auto_restart: bool = True
    restart_delay_seconds: int = 10
    watchdog_enabled: bool = True
    watchdog_timeout_seconds: int = 60


@dataclass
class AraConfig:
    """Main Ara Voice Assistant configuration."""

    wake_word: WakeWordConfig = field(default_factory=WakeWordConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    mode: ModeConfig = field(default_factory=ModeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    feedback: FeedbackConfig = field(default_factory=FeedbackConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    cloud: CloudConfig = field(default_factory=CloudConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    dev: DevConfig = field(default_factory=DevConfig)
    production: ProductionConfig = field(default_factory=ProductionConfig)


class ConfigLoader(Protocol):
    """Protocol for configuration loading."""

    def load(self, path: Path) -> AraConfig:
        """Load configuration from file path."""
        ...

    def load_profile(self, profile: str) -> AraConfig:
        """Load configuration by profile name (dev, prod)."""
        ...

    def get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        ...


# Public API
__all__ = [
    "AraConfig",
    "AudioConfig",
    "CloudConfig",
    "ConfigLoader",
    "DevConfig",
    "FeedbackConfig",
    "LLMConfig",
    "LoggingConfig",
    "ModeConfig",
    "PerformanceConfig",
    "ProductionConfig",
    "STTConfig",
    "TTSConfig",
    "TestingConfig",
    "UserProfile",
    "WakeWordConfig",
    "load_user_profile",
    "save_user_profile",
]
