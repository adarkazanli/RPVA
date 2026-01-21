"""Claude query module for Ara Voice Assistant.

Provides integration with Claude API for advanced AI queries via voice.
"""

from .client import ClaudeClient, ClaudeClientConfig, ClaudeResponse
from .errors import (
    ClaudeAPIError,
    ClaudeAuthError,
    ClaudeConnectivityError,
    ClaudeError,
    ClaudeTimeoutError,
)
from .handler import ClaudeHandler
from .session import ClaudeSession

__all__ = [
    "ClaudeAPIError",
    "ClaudeAuthError",
    "ClaudeClient",
    "ClaudeClientConfig",
    "ClaudeConnectivityError",
    "ClaudeError",
    "ClaudeHandler",
    "ClaudeResponse",
    "ClaudeSession",
    "ClaudeTimeoutError",
]
