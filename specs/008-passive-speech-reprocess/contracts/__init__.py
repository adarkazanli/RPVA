"""
Design Contracts for 008-passive-speech-reprocess

These protocols define the interfaces for the interrupt handling system.
Implementation files will import and implement these contracts.
"""

from .interrupt_manager import (
    BufferSegment,
    ContinuationWindow,
    InterruptEvent,
    InterruptManager,
    InterruptState,
    RequestBuffer,
    CONTINUATION_WINDOW_S,
    INTERRUPT_FEEDBACK_FREQ,
    INTERRUPT_FEEDBACK_MS,
    INTERRUPT_THRESHOLD,
    SILENCE_TIMEOUT_MS,
    TTS_STOP_TIMEOUT_MS,
)
from .playback_extensions import InterruptiblePlayback

__all__ = [
    "InterruptState",
    "BufferSegment",
    "InterruptEvent",
    "RequestBuffer",
    "ContinuationWindow",
    "InterruptManager",
    "InterruptiblePlayback",
    "INTERRUPT_THRESHOLD",
    "SILENCE_TIMEOUT_MS",
    "CONTINUATION_WINDOW_S",
    "TTS_STOP_TIMEOUT_MS",
    "INTERRUPT_FEEDBACK_FREQ",
    "INTERRUPT_FEEDBACK_MS",
]
