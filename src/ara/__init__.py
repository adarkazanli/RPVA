"""Ara Voice Assistant - Offline-first voice assistant for Raspberry Pi.

Ara provides natural voice interaction with:
- Wake word detection ("Ara")
- Speech-to-text (Whisper)
- Local LLM responses (Ollama)
- Text-to-speech (Piper)

Designed for Raspberry Pi 4 deployment with <6s end-to-end latency.

Usage:
    python -m ara --config config/dev.yaml
    python -m ara --profile prod
"""

__version__ = "0.1.0"
__author__ = "MPS Inc"

from .config import AraConfig
from .config.loader import load_config

__all__ = [
    "AraConfig",
    "__version__",
    "load_config",
]
