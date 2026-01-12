"""Router module for Ara Voice Assistant.

Provides orchestration of the voice interaction pipeline.
"""

from .orchestrator import InteractionResult, Orchestrator

__all__ = [
    "InteractionResult",
    "Orchestrator",
]
