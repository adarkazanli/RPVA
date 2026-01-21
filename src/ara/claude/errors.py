"""Error types for Claude query module.

Custom exceptions for Claude API interactions.
"""


class ClaudeError(Exception):
    """Base exception for Claude-related errors."""

    pass


class ClaudeTimeoutError(ClaudeError):
    """Raised when Claude API request times out."""

    pass


class ClaudeAPIError(ClaudeError):
    """Raised when Claude API returns an error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize API error.

        Args:
            message: Error message.
            status_code: HTTP status code if available.
        """
        super().__init__(message)
        self.status_code = status_code


class ClaudeAuthError(ClaudeError):
    """Raised when authentication fails."""

    pass


class ClaudeConnectivityError(ClaudeError):
    """Raised when internet connectivity check fails."""

    pass


__all__ = [
    "ClaudeAPIError",
    "ClaudeAuthError",
    "ClaudeConnectivityError",
    "ClaudeError",
    "ClaudeTimeoutError",
]
