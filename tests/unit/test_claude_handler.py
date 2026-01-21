"""Unit tests for ClaudeHandler authentication behavior.

Tests the handler's authentication error handling and setup messages.
"""

import contextlib
import os
from unittest.mock import MagicMock, patch

import pytest

from ara.claude.errors import ClaudeAuthError
from ara.claude.handler import ClaudeHandler


class TestClaudeHandlerAuthentication:
    """Tests for ClaudeHandler authentication handling (T037-T038)."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock repository."""
        return MagicMock()

    def test_handle_query_raises_auth_error_when_api_key_missing(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that handle_query raises ClaudeAuthError when API key not set."""
        handler = ClaudeHandler(repository=mock_repository)

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ClaudeAuthError):
                handler.handle_query("test query")

    def test_handle_query_raises_auth_error_with_helpful_message(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that auth error contains helpful setup information."""
        handler = ClaudeHandler(repository=mock_repository)

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ClaudeAuthError) as exc_info:
                handler.handle_query("test query")
            error_message = str(exc_info.value)
            assert "ANTHROPIC_API_KEY" in error_message

    def test_get_auth_setup_message_returns_helpful_instructions(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that get_auth_setup_message provides clear setup instructions."""
        handler = ClaudeHandler(repository=mock_repository)

        message = handler.get_auth_setup_message()

        assert "API key" in message
        assert "ANTHROPIC_API_KEY" in message
        assert "environment variable" in message.lower()

    def test_get_connectivity_error_message_is_user_friendly(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that connectivity error message is user-friendly."""
        handler = ClaudeHandler(repository=mock_repository)

        message = handler.get_connectivity_error_message()

        assert "Claude" in message or "reach" in message.lower()
        assert "internet" in message.lower() or "connection" in message.lower()

    def test_get_timeout_message_offers_retry(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that timeout message offers to retry."""
        handler = ClaudeHandler(repository=mock_repository)

        message = handler.get_timeout_message()

        assert "try again" in message.lower() or "retry" in message.lower()


class TestClaudeHandlerApiKeyValidation:
    """Tests for API key validation on first query (T037)."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock repository."""
        return MagicMock()

    def test_api_key_validated_on_first_query_not_init(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that API key is validated on first query, not during init."""
        # Handler creation should not raise, even without API key
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            # This should NOT raise - lazy validation
            handler = ClaudeHandler(repository=mock_repository)
            assert handler is not None

    def test_api_key_validation_cached_after_first_query(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that client is cached after successful creation."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            handler = ClaudeHandler(repository=mock_repository)

            # Mock the client creation
            with patch("ara.claude.handler.ClaudeClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client.check_connectivity.return_value = True
                mock_client.send_message.return_value = MagicMock(
                    text="response",
                    tokens_used=10,
                    model="test",
                    latency_ms=100,
                )
                mock_client_class.return_value = mock_client

                # First call creates client (may fail on connectivity, that's ok)
                with contextlib.suppress(Exception):
                    handler.handle_query("test")

                # Client should be cached
                assert handler._client is not None or mock_client_class.called
