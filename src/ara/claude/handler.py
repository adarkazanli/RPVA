"""Handler for Claude query operations.

Orchestrates Claude API calls, storage, and response processing.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from ara.claude.client import ClaudeClient, ClaudeClientConfig
from ara.claude.errors import (
    ClaudeAPIError,
    ClaudeAuthError,
    ClaudeConnectivityError,
    ClaudeTimeoutError,
)
from ara.claude.session import ClaudeSession

if TYPE_CHECKING:
    from ara.feedback import AudioFeedback
    from ara.storage.claude_repository import ClaudeRepository

logger = logging.getLogger(__name__)


class ClaudeHandler:
    """Handler for Claude query operations."""

    def __init__(
        self,
        repository: ClaudeRepository,
        config: ClaudeClientConfig | None = None,
        feedback: AudioFeedback | None = None,
        followup_window_seconds: float = 5.0,
    ) -> None:
        """Initialize handler.

        Args:
            repository: Repository for storing queries and responses.
            config: Optional client config. If not provided, loads from environment.
            feedback: Optional audio feedback for waiting indicator.
            followup_window_seconds: Duration of follow-up window after response.
        """
        self._repository = repository
        self._config = config
        self._feedback = feedback
        self._client: ClaudeClient | None = None
        self._session = ClaudeSession(followup_window_seconds=followup_window_seconds)

    def _get_client(self) -> ClaudeClient:
        """Get or create Claude client.

        Returns:
            ClaudeClient instance.

        Raises:
            ClaudeAuthError: If API key is not configured.
        """
        if self._client is None:
            try:
                config = self._config or ClaudeClientConfig.from_env()
                self._client = ClaudeClient(config)
            except ValueError as e:
                raise ClaudeAuthError(str(e)) from e
        return self._client

    def handle_query(
        self,
        query: str,
        session_id: str | None = None,
        is_followup: bool = False,
    ) -> str:
        """Handle a Claude query request.

        Args:
            query: The user's query text.
            session_id: Optional session identifier (uses internal session if not provided).
            is_followup: Whether this is a follow-up question.

        Returns:
            Response text from Claude.

        Raises:
            ClaudeError: If any error occurs during processing.
        """
        from ara.feedback.waiting import WaitingIndicator

        timestamp = datetime.now(UTC)
        effective_session_id = session_id or self._session.session_id

        # Get client (validates authentication)
        client = self._get_client()

        # Check connectivity before making request
        try:
            client.check_connectivity()
        except ClaudeConnectivityError:
            raise

        # Save query to storage
        query_id = self._repository.save_query(
            session_id=effective_session_id,
            utterance=query,
            is_followup=is_followup,
            timestamp=timestamp,
        )
        logger.debug(f"Saved query {query_id}: {query[:50]}...")

        # Add user message to session for context
        self._session.add_user_message(query)

        # Create waiting indicator if feedback is available
        waiting_indicator: WaitingIndicator | None = None
        if self._feedback is not None:
            waiting_indicator = WaitingIndicator(self._feedback)

        try:
            # Start waiting indicator before API call
            if waiting_indicator:
                waiting_indicator.start()

            # Send query to Claude API with session context
            response = client.send_message(query, session=self._session)

            # Add assistant message to session
            self._session.add_assistant_message(response.text)

            # Save response to storage
            response_timestamp = datetime.now(UTC)
            self._repository.save_response(
                query_id=query_id,
                session_id=effective_session_id,
                text=response.text,
                tokens_used=response.tokens_used,
                model=response.model,
                latency_ms=response.latency_ms,
                timestamp=response_timestamp,
            )
            logger.debug(
                f"Received response ({response.tokens_used} tokens, "
                f"{response.latency_ms}ms): {response.text[:50]}..."
            )

            return response.text

        except ClaudeTimeoutError:
            logger.warning(f"Claude API request timed out for query: {query[:50]}...")
            raise
        except ClaudeAuthError:
            logger.error("Claude API authentication failed")
            raise
        except ClaudeAPIError as e:
            logger.error(f"Claude API error: {e}")
            raise
        finally:
            # Always stop waiting indicator
            if waiting_indicator:
                waiting_indicator.stop()

    def is_in_followup_window(self) -> bool:
        """Check if currently within the follow-up window.

        Returns:
            True if within the follow-up window, False otherwise.
        """
        return self._session.is_in_followup_window()

    def reset_session(self) -> None:
        """Reset the conversation session.

        Clears message history and ends the follow-up window.
        """
        self._session.reset()
        logger.debug("Claude session reset")

    def handle_reset(self) -> str:
        """Handle a reset/new conversation request.

        Clears the conversation history and returns a confirmation message.

        Returns:
            Confirmation message for the user.
        """
        had_history = self._session.has_history
        self.reset_session()

        if had_history:
            return (
                "I've cleared our conversation history. "
                "What would you like to talk about?"
            )
        else:
            return "Starting a new conversation. How can I help you?"

    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self._session.session_id

    @property
    def has_conversation_history(self) -> bool:
        """Check if there's existing conversation history."""
        return self._session.has_history

    def get_auth_setup_message(self) -> str:
        """Get message to display when authentication is not configured.

        Returns:
            User-friendly message about setting up authentication.
        """
        return (
            "To use Claude, please set up your API key. "
            "Set the ANTHROPIC_API_KEY environment variable with your Claude API key."
        )

    def get_connectivity_error_message(self) -> str:
        """Get message to display when connectivity check fails.

        Returns:
            User-friendly message about connectivity issues.
        """
        return (
            "I can't reach Claude right now. "
            "Please check your internet connection and try again."
        )

    def get_timeout_message(self) -> str:
        """Get message to display when request times out.

        Returns:
            User-friendly message about timeout with retry option.
        """
        return (
            "Claude is taking longer than expected to respond. "
            "Would you like me to try again?"
        )

    def handle_summary_request(self, period: str | None = None) -> str:
        """Handle a request to summarize Claude conversation history.

        Args:
            period: Time period for summary (today, yesterday, week, month).
                   Defaults to today if not specified.

        Returns:
            Summary text of conversations in the specified period.
        """
        now = datetime.now(UTC)
        period = period or "today"

        # Calculate date range based on period
        if period == "yesterday":
            start = (now - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = start + timedelta(days=1) - timedelta(microseconds=1)
            period_desc = "yesterday"
        elif period == "week":
            # Start from beginning of this week (Monday)
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = now
            period_desc = "this week"
        elif period == "month":
            # Start from beginning of this month
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
            period_desc = "this month"
        else:  # today
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
            period_desc = "today"

        # Get conversations from repository
        conversations = self._repository.get_conversations_for_period(start, end)

        if not conversations:
            return f"You haven't had any Claude conversations {period_desc}."

        # Format summary
        summary_parts = []
        summary_parts.append(
            f"You had {len(conversations)} conversation{'s' if len(conversations) != 1 else ''} "
            f"with Claude {period_desc}:"
        )

        for i, (query, response) in enumerate(reversed(conversations), 1):
            utterance = query.get("utterance", "Unknown question")
            # Truncate long questions for readability
            if len(utterance) > 100:
                utterance = utterance[:97] + "..."

            if response:
                response_text = response.get("text", "No response")
                # Truncate long responses
                if len(response_text) > 150:
                    response_text = response_text[:147] + "..."
                summary_parts.append(f"{i}. Asked: {utterance}")
                summary_parts.append(f"   Claude: {response_text}")
            else:
                summary_parts.append(f"{i}. Asked: {utterance} (no response)")

        return "\n".join(summary_parts)


__all__ = ["ClaudeHandler"]
