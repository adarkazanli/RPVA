# Module Contracts: Claude Query Mode

**Feature**: 009-claude-query-mode
**Date**: 2026-01-21

This document defines the internal module interfaces for the Claude Query Mode feature.

## Module: `ara.claude`

### ClaudeClient

Wrapper around Anthropic API with Ara-specific configuration.

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class ClaudeClientConfig:
    """Configuration for Claude client."""
    api_key: str
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 500
    temperature: float = 0.7
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "ClaudeClientConfig":
        """Create config from environment variables."""
        ...


class ClaudeClient(Protocol):
    """Protocol for Claude API client."""

    async def send_message(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
    ) -> "ClaudeQueryResult":
        """Send a message to Claude.

        Args:
            message: User's query text.
            conversation_history: Previous messages for context.
            system_prompt: Optional system prompt override.

        Returns:
            ClaudeQueryResult with response text and metadata.

        Raises:
            ClaudeTimeoutError: If request exceeds timeout.
            ClaudeAPIError: If API returns an error.
            ClaudeAuthError: If authentication fails.
        """
        ...

    def check_connectivity(self) -> bool:
        """Check if Claude API is reachable.

        Returns:
            True if API endpoint is reachable within 2 seconds.
        """
        ...


@dataclass
class ClaudeQueryResult:
    """Result from a Claude query."""
    text: str
    tokens_used: int
    model: str
    latency_ms: int
```

### ClaudeSession

Manages conversation context for follow-up questions.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
import uuid


@dataclass
class ConversationMessage:
    """A single message in the conversation."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime


class ClaudeSession:
    """Manages conversation state with Claude."""

    def __init__(self, max_messages: int = 20) -> None:
        """Initialize a new session.

        Args:
            max_messages: Maximum messages to retain in history.
        """
        ...

    @property
    def session_id(self) -> str:
        """Get the unique session ID."""
        ...

    @property
    def messages(self) -> list[ConversationMessage]:
        """Get conversation history."""
        ...

    @property
    def is_active(self) -> bool:
        """Check if session has any messages."""
        ...

    def add_user_message(self, content: str) -> None:
        """Add a user message to history.

        Args:
            content: The user's message text.
        """
        ...

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant (Claude) message to history.

        Args:
            content: Claude's response text.
        """
        ...

    def get_api_messages(self) -> list[dict[str, str]]:
        """Get messages formatted for Claude API.

        Returns:
            List of {"role": str, "content": str} dicts.
        """
        ...

    def reset(self) -> None:
        """Clear conversation history and start fresh."""
        ...
```

### ClaudeHandler

Intent handler for Claude queries.

```python
from typing import Protocol

class ClaudeHandler(Protocol):
    """Handler for Claude query intents."""

    async def handle_query(
        self,
        query: str,
        is_followup: bool = False,
    ) -> str:
        """Handle a Claude query.

        Args:
            query: User's question text.
            is_followup: Whether this is a follow-up in active conversation.

        Returns:
            Response text to speak to user.
        """
        ...

    async def handle_summary_request(
        self,
        period: Literal["today", "this_week", "this_month"],
    ) -> str:
        """Handle a request to summarize Claude conversations.

        Args:
            period: Time period to summarize.

        Returns:
            Summary text to speak to user.
        """
        ...

    def handle_reset(self) -> str:
        """Handle conversation reset request.

        Returns:
            Confirmation message to speak.
        """
        ...
```

## Module: `ara.storage.claude_repository`

### ClaudeRepository

MongoDB repository for Claude queries and responses.

```python
from datetime import datetime
from typing import Protocol

from bson import ObjectId


class ClaudeRepository(Protocol):
    """Repository for Claude query storage."""

    def save_query(
        self,
        session_id: str,
        utterance: str,
        is_followup: bool,
        timestamp: datetime,
    ) -> str:
        """Save a Claude query.

        Args:
            session_id: Session UUID.
            utterance: Original user speech.
            is_followup: Whether query was in follow-up window.
            timestamp: When query was received.

        Returns:
            Document ID of saved query.
        """
        ...

    def save_response(
        self,
        query_id: str,
        session_id: str,
        text: str,
        tokens_used: int,
        model: str,
        latency_ms: int,
        timestamp: datetime,
    ) -> str:
        """Save a Claude response.

        Args:
            query_id: Reference to the query.
            session_id: Session UUID.
            text: Response text from Claude.
            tokens_used: Total tokens consumed.
            model: Claude model used.
            latency_ms: API response time.
            timestamp: When response was received.

        Returns:
            Document ID of saved response.
        """
        ...

    def get_queries_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> list[dict]:
        """Get queries within a date range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            limit: Maximum results to return.

        Returns:
            List of query documents, most recent first.
        """
        ...

    def get_response_for_query(self, query_id: str) -> dict | None:
        """Get response for a specific query.

        Args:
            query_id: Query document ID.

        Returns:
            Response document or None if not found.
        """
        ...

    def get_conversations_for_period(
        self,
        start: datetime,
        end: datetime,
    ) -> list[tuple[dict, dict | None]]:
        """Get query-response pairs for a time period.

        Args:
            start: Start datetime.
            end: End datetime.

        Returns:
            List of (query, response) tuples for summarization.
        """
        ...
```

## Module: `ara.router.intent`

### New Intent Types

```python
class IntentType(Enum):
    # ... existing types ...

    # New Claude-related intents
    CLAUDE_QUERY = "claude_query"           # "ask Claude X"
    CLAUDE_SUMMARY = "claude_summary"       # "summarize my Claude conversations"
    CLAUDE_RESET = "claude_reset"           # "new conversation" (during Claude mode)
```

### New Intent Patterns

```python
# Added to IntentClassifier

CLAUDE_QUERY_PATTERNS = [
    r"ask\s+claude\s+(.+)",
    r"ask\s+claud\s+(.+)",          # Common mishearing
    r"hey\s+claude[,\s]+(.+)",
    r"claude[,\s]+(.+)",            # Direct address
]

CLAUDE_SUMMARY_PATTERNS = [
    r"summarize\s+(?:my\s+)?(?:claude\s+)?conversations?\s+(?:from\s+)?(today|this\s+week|this\s+month)",
    r"what\s+(?:are\s+)?(?:the\s+)?key\s+learnings?\s+from\s+claude\s+(today|this\s+week|this\s+month)",
    r"summarize\s+(?:my\s+)?claude\s+(?:queries|questions)\s+(today|this\s+week|this\s+month)",
]

CLAUDE_RESET_PATTERNS = [
    r"new\s+conversation",
    r"start\s+over",
    r"clear\s+(?:the\s+)?(?:claude\s+)?(?:conversation|history)",
    r"reset\s+(?:the\s+)?(?:claude\s+)?conversation",
]
```

## Module: `ara.feedback`

### New Feedback Type

```python
class FeedbackType(Enum):
    # ... existing types ...

    CLAUDE_WAITING = "claude_waiting"  # Musical loop while waiting for response
```

### Waiting Indicator Control

```python
class WaitingIndicator(Protocol):
    """Control for the Claude waiting indicator."""

    def start(self) -> None:
        """Start playing the waiting indicator loop."""
        ...

    def stop(self) -> None:
        """Stop the waiting indicator immediately."""
        ...

    @property
    def is_playing(self) -> bool:
        """Check if indicator is currently playing."""
        ...
```

## Error Types

```python
class ClaudeError(Exception):
    """Base exception for Claude-related errors."""
    pass


class ClaudeTimeoutError(ClaudeError):
    """Raised when Claude API request times out."""
    pass


class ClaudeAPIError(ClaudeError):
    """Raised when Claude API returns an error."""
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ClaudeAuthError(ClaudeError):
    """Raised when authentication fails."""
    pass


class ClaudeConnectivityError(ClaudeError):
    """Raised when internet connectivity check fails."""
    pass
```

## Integration Points

### Orchestrator Integration

The `ClaudeHandler` integrates with the existing orchestrator:

1. **Intent Detection**: `IntentClassifier.classify()` returns `CLAUDE_QUERY` intent
2. **Handler Dispatch**: Orchestrator routes to `ClaudeHandler.handle_query()`
3. **Feedback Loop**: Handler uses `WaitingIndicator` during API call
4. **TTS Output**: Response text passed to existing TTS system
5. **Follow-up Window**: 5-second timer started after response

### Storage Integration

- `ClaudeRepository` uses existing `MongoStorageClient.database`
- New collection `claude_queries` created automatically on first write
- Indexes created on repository initialization (same pattern as `InteractionRepository`)
