"""Session management for Claude conversations.

Provides conversation history and follow-up window tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


@dataclass
class Message:
    """A single message in the conversation."""

    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ClaudeSession:
    """Manages conversation state for Claude interactions.

    Tracks message history for multi-turn conversations and manages
    the follow-up window timing for natural conversation flow.

    The follow-up window allows users to ask follow-up questions
    without needing to use the trigger phrase ("ask Claude") within
    a configurable time window after receiving a response.

    Example:
        session = ClaudeSession()
        session.add_user_message("What is Python?")
        session.add_assistant_message("Python is a programming language...")

        # Within 5 seconds, user can ask follow-up without trigger
        if session.is_in_followup_window():
            session.add_user_message("What are its main features?")
    """

    DEFAULT_FOLLOWUP_WINDOW = 5.0  # seconds

    def __init__(
        self,
        session_id: str | None = None,
        followup_window_seconds: float = DEFAULT_FOLLOWUP_WINDOW,
    ) -> None:
        """Initialize a new Claude session.

        Args:
            session_id: Optional session identifier. Generated if not provided.
            followup_window_seconds: Duration of follow-up window after response.
        """
        self._session_id = session_id or str(uuid.uuid4())
        self._messages: list[Message] = []
        self._followup_window_seconds = followup_window_seconds
        self._last_response_time: datetime | None = None

    @property
    def session_id(self) -> str:
        """Get the session identifier."""
        return self._session_id

    @property
    def message_count(self) -> int:
        """Get the number of messages in the session."""
        return len(self._messages)

    @property
    def has_history(self) -> bool:
        """Return True if session has any message history."""
        return len(self._messages) > 0

    @property
    def followup_window_seconds(self) -> float:
        """Get the follow-up window duration in seconds."""
        return self._followup_window_seconds

    @property
    def last_response_time(self) -> datetime | None:
        """Get the timestamp of the last assistant response."""
        return self._last_response_time

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation.

        Args:
            content: The message content from the user.
        """
        message = Message(role="user", content=content)
        self._messages.append(message)

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation.

        This also updates the last response time for follow-up window tracking.

        Args:
            content: The response content from Claude.
        """
        message = Message(role="assistant", content=content)
        self._messages.append(message)
        self._last_response_time = datetime.now(UTC)

    def get_api_messages(self) -> list[dict[str, str]]:
        """Get messages in Claude API format.

        Returns:
            List of message dicts with 'role' and 'content' keys.
        """
        return [{"role": msg.role, "content": msg.content} for msg in self._messages]

    def reset(self) -> None:
        """Clear all message history and reset follow-up window.

        The session ID is preserved after reset.
        """
        self._messages.clear()
        self._last_response_time = None

    def is_in_followup_window(self) -> bool:
        """Check if currently within the follow-up window.

        The follow-up window is active for a configurable duration
        after receiving an assistant response.

        Returns:
            True if within the follow-up window, False otherwise.
        """
        if self._last_response_time is None:
            return False

        elapsed = (datetime.now(UTC) - self._last_response_time).total_seconds()
        return elapsed < self._followup_window_seconds

    def time_remaining_in_window(self) -> float:
        """Get the time remaining in the follow-up window.

        Returns:
            Seconds remaining in window, or 0.0 if not in window.
        """
        if self._last_response_time is None:
            return 0.0

        elapsed = (datetime.now(UTC) - self._last_response_time).total_seconds()
        remaining = self._followup_window_seconds - elapsed
        return max(0.0, remaining)

    def extend_followup_window(self, additional_seconds: float) -> None:
        """Extend the follow-up window by adding time.

        This can be used to keep the window open during user speech.

        Args:
            additional_seconds: Additional seconds to add to the window.
        """
        if self._last_response_time is not None:
            # Effectively extend by pushing the last response time forward
            self._followup_window_seconds += additional_seconds


__all__ = ["ClaudeSession", "Message"]
