"""Unit tests for Claude client.

Tests the ClaudeClient class for API communication.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from ara.claude.client import ClaudeClientConfig


class TestClaudeClientConfig:
    """Tests for ClaudeClientConfig."""

    def test_from_env_returns_config_with_api_key(self) -> None:
        """Test that from_env() returns config with API key from environment."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-api-key"}):
            config = ClaudeClientConfig.from_env()
            assert config.api_key == "test-api-key"
            assert config.model == "claude-sonnet-4-20250514"
            assert config.max_tokens == 500
            assert config.timeout_seconds == 30.0

    def test_from_env_raises_when_api_key_missing(self) -> None:
        """Test that from_env() raises ValueError when API key not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure ANTHROPIC_API_KEY is not set
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                ClaudeClientConfig.from_env()

    def test_from_env_raises_when_api_key_empty(self) -> None:
        """Test that from_env() raises ValueError when API key is empty string."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}),
            pytest.raises(ValueError, match="ANTHROPIC_API_KEY"),
        ):
            ClaudeClientConfig.from_env()

    def test_from_env_error_message_is_helpful(self) -> None:
        """Test that missing API key error message provides setup guidance."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(ValueError) as exc_info:
                ClaudeClientConfig.from_env()
            error_message = str(exc_info.value)
            assert "ANTHROPIC_API_KEY" in error_message
            assert "environment variable" in error_message.lower()

    def test_config_defaults(self) -> None:
        """Test default configuration values."""
        config = ClaudeClientConfig(api_key="test-key")
        assert config.model == "claude-sonnet-4-20250514"
        assert config.max_tokens == 500
        assert config.temperature == 0.7
        assert config.timeout_seconds == 30.0

    def test_config_custom_values(self) -> None:
        """Test custom configuration values."""
        config = ClaudeClientConfig(
            api_key="test-key",
            model="claude-opus-4-20250514",
            max_tokens=1000,
            temperature=0.5,
            timeout_seconds=60.0,
        )
        assert config.model == "claude-opus-4-20250514"
        assert config.max_tokens == 1000
        assert config.temperature == 0.5
        assert config.timeout_seconds == 60.0


class TestClaudeClientSendMessage:
    """Tests for ClaudeClient.send_message() method."""

    @pytest.fixture
    def mock_anthropic(self) -> MagicMock:
        """Create mock Anthropic client."""
        mock = MagicMock()
        mock.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Claude's response")],
            usage=MagicMock(input_tokens=10, output_tokens=20),
            model="claude-sonnet-4-20250514",
        )
        return mock

    def test_send_message_returns_response(self, mock_anthropic: MagicMock) -> None:
        """Test that send_message returns Claude's response."""
        from ara.claude.client import ClaudeClient, ClaudeClientConfig

        config = ClaudeClientConfig(api_key="test-key")
        with patch("ara.claude.client.anthropic.Anthropic", return_value=mock_anthropic):
            client = ClaudeClient(config)
            response = client.send_message("test query")
            assert response.text == "Claude's response"
            assert response.tokens_used == 30  # 10 input + 20 output

    def test_send_message_passes_system_prompt(self, mock_anthropic: MagicMock) -> None:
        """Test that system prompt is included in API call."""
        from ara.claude.client import SYSTEM_PROMPT, ClaudeClient, ClaudeClientConfig

        config = ClaudeClientConfig(api_key="test-key")
        with patch("ara.claude.client.anthropic.Anthropic", return_value=mock_anthropic):
            client = ClaudeClient(config)
            client.send_message("test query")
            call_kwargs = mock_anthropic.messages.create.call_args[1]
            assert call_kwargs["system"] == SYSTEM_PROMPT

    def test_send_message_respects_max_tokens(self, mock_anthropic: MagicMock) -> None:
        """Test that max_tokens limit is passed to API."""
        from ara.claude.client import ClaudeClient, ClaudeClientConfig

        config = ClaudeClientConfig(api_key="test-key", max_tokens=200)
        with patch("ara.claude.client.anthropic.Anthropic", return_value=mock_anthropic):
            client = ClaudeClient(config)
            client.send_message("test query")
            call_kwargs = mock_anthropic.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 200

    def test_send_message_handles_timeout(self, mock_anthropic: MagicMock) -> None:
        """Test that timeout errors are raised as ClaudeTimeoutError."""
        import anthropic

        from ara.claude.client import ClaudeClient, ClaudeClientConfig
        from ara.claude.errors import ClaudeTimeoutError

        mock_anthropic.messages.create.side_effect = anthropic.APITimeoutError(
            request=MagicMock()
        )
        config = ClaudeClientConfig(api_key="test-key")
        with patch("ara.claude.client.anthropic.Anthropic", return_value=mock_anthropic):
            client = ClaudeClient(config)
            with pytest.raises(ClaudeTimeoutError):
                client.send_message("test query")

    def test_send_message_handles_api_error(self, mock_anthropic: MagicMock) -> None:
        """Test that API errors are raised as ClaudeAPIError."""
        import anthropic

        from ara.claude.client import ClaudeClient, ClaudeClientConfig
        from ara.claude.errors import ClaudeAPIError

        mock_anthropic.messages.create.side_effect = anthropic.APIStatusError(
            message="Server error",
            response=MagicMock(status_code=500),
            body=None,
        )
        config = ClaudeClientConfig(api_key="test-key")
        with patch("ara.claude.client.anthropic.Anthropic", return_value=mock_anthropic):
            client = ClaudeClient(config)
            with pytest.raises(ClaudeAPIError):
                client.send_message("test query")

    def test_send_message_handles_auth_error(self, mock_anthropic: MagicMock) -> None:
        """Test that auth errors are raised as ClaudeAuthError."""
        import anthropic

        from ara.claude.client import ClaudeClient, ClaudeClientConfig
        from ara.claude.errors import ClaudeAuthError

        mock_anthropic.messages.create.side_effect = anthropic.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body=None,
        )
        config = ClaudeClientConfig(api_key="test-key")
        with patch("ara.claude.client.anthropic.Anthropic", return_value=mock_anthropic):
            client = ClaudeClient(config)
            with pytest.raises(ClaudeAuthError):
                client.send_message("test query")


class TestClaudeClientConnectivity:
    """Tests for ClaudeClient.check_connectivity() method (T049)."""

    def test_check_connectivity_returns_true_when_connected(self) -> None:
        """Test that check_connectivity returns True when API is reachable."""
        from ara.claude.client import ClaudeClient, ClaudeClientConfig

        config = ClaudeClientConfig(api_key="test-key")
        with (
            patch("ara.claude.client.anthropic.Anthropic"),
            patch("ara.claude.client.socket.create_connection") as mock_socket,
        ):
            mock_socket.return_value = MagicMock()
            client = ClaudeClient(config)
            result = client.check_connectivity()
            assert result is True

    def test_check_connectivity_raises_on_timeout(self) -> None:
        """Test that check_connectivity raises ClaudeConnectivityError on timeout."""
        from ara.claude.client import ClaudeClient, ClaudeClientConfig
        from ara.claude.errors import ClaudeConnectivityError

        config = ClaudeClientConfig(api_key="test-key")
        with (
            patch("ara.claude.client.anthropic.Anthropic"),
            patch("ara.claude.client.socket.create_connection") as mock_socket,
        ):
            mock_socket.side_effect = TimeoutError("Connection timed out")
            client = ClaudeClient(config)
            with pytest.raises(ClaudeConnectivityError) as exc_info:
                client.check_connectivity()
            assert "internet connection" in str(exc_info.value).lower()

    def test_check_connectivity_raises_error_with_details(self) -> None:
        """Test that connectivity errors include details."""
        import socket

        from ara.claude.client import ClaudeClient, ClaudeClientConfig
        from ara.claude.errors import ClaudeConnectivityError

        config = ClaudeClientConfig(api_key="test-key")
        with (
            patch("ara.claude.client.anthropic.Anthropic"),
            patch("ara.claude.client.socket.create_connection") as mock_socket,
        ):
            mock_socket.side_effect = socket.gaierror("Name resolution failed")
            client = ClaudeClient(config)
            with pytest.raises(ClaudeConnectivityError) as exc_info:
                client.check_connectivity()
            error_msg = str(exc_info.value)
            assert "Claude API" in error_msg or "internet" in error_msg.lower()


class TestClaudeClientTimeout:
    """Tests for timeout handling (T050)."""

    def test_client_configured_with_30_second_default_timeout(self) -> None:
        """Test that default timeout is 30 seconds."""
        from ara.claude.client import ClaudeClientConfig

        config = ClaudeClientConfig(api_key="test-key")
        assert config.timeout_seconds == 30.0

    def test_client_passes_timeout_to_anthropic(self) -> None:
        """Test that timeout is passed to Anthropic client."""
        from ara.claude.client import ClaudeClient, ClaudeClientConfig

        config = ClaudeClientConfig(api_key="test-key", timeout_seconds=45.0)
        with patch("ara.claude.client.anthropic.Anthropic") as mock_anthropic_cls:
            ClaudeClient(config)
            mock_anthropic_cls.assert_called_once_with(
                api_key="test-key",
                timeout=45.0,
            )

    def test_timeout_error_message_mentions_retry(self) -> None:
        """Test that timeout error from handler suggests retry."""
        from ara.claude.handler import ClaudeHandler

        mock_repo = MagicMock()
        handler = ClaudeHandler(repository=mock_repo)
        message = handler.get_timeout_message()
        assert "try again" in message.lower()
