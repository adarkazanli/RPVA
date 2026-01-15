"""Unit tests for EmailConfig."""

import os
from unittest.mock import patch

import pytest

from ara.email.config import EmailConfig


class TestEmailConfigFromEnv:
    """Tests for EmailConfig.from_env() class method."""

    def test_from_env_returns_config_when_all_vars_present(self) -> None:
        """Should return EmailConfig when all required env vars are set."""
        env_vars = {
            "EMAIL_ADDRESS": "test@example.com",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret123",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = EmailConfig.from_env()

        assert config is not None
        assert config.recipient_address == "test@example.com"
        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.smtp_user == "user@example.com"
        assert config.smtp_pass == "secret123"

    def test_from_env_returns_none_when_email_address_missing(self) -> None:
        """Should return None when EMAIL_ADDRESS is not set."""
        env_vars = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = EmailConfig.from_env()

        assert config is None

    def test_from_env_returns_none_when_smtp_host_missing(self) -> None:
        """Should return None when SMTP_HOST is not set."""
        env_vars = {
            "EMAIL_ADDRESS": "test@example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = EmailConfig.from_env()

        assert config is None

    def test_from_env_uses_default_port_when_not_specified(self) -> None:
        """Should use default port 587 when SMTP_PORT is not set."""
        env_vars = {
            "EMAIL_ADDRESS": "test@example.com",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_USER": "user@example.com",
            "SMTP_PASS": "secret123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = EmailConfig.from_env()

        assert config is not None
        assert config.smtp_port == 587

    def test_from_env_returns_none_when_smtp_user_missing(self) -> None:
        """Should return None when SMTP_USER is not set."""
        env_vars = {
            "EMAIL_ADDRESS": "test@example.com",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_PASS": "secret123",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = EmailConfig.from_env()

        assert config is None

    def test_from_env_returns_none_when_smtp_pass_missing(self) -> None:
        """Should return None when SMTP_PASS is not set."""
        env_vars = {
            "EMAIL_ADDRESS": "test@example.com",
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "user@example.com",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = EmailConfig.from_env()

        assert config is None


class TestEmailConfigIsValid:
    """Tests for EmailConfig.is_valid() method."""

    def test_is_valid_returns_true_for_valid_config(self) -> None:
        """Should return True when all fields are valid."""
        config = EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )
        assert config.is_valid() is True

    def test_is_valid_returns_false_for_empty_recipient(self) -> None:
        """Should return False when recipient_address is empty."""
        config = EmailConfig(
            recipient_address="",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )
        assert config.is_valid() is False

    def test_is_valid_returns_false_for_empty_host(self) -> None:
        """Should return False when smtp_host is empty."""
        config = EmailConfig(
            recipient_address="test@example.com",
            smtp_host="",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )
        assert config.is_valid() is False

    def test_is_valid_returns_false_for_invalid_port(self) -> None:
        """Should return False when smtp_port is out of range."""
        config = EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=0,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )
        assert config.is_valid() is False

        config_high = EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=70000,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )
        assert config_high.is_valid() is False

    def test_is_valid_returns_false_for_empty_user(self) -> None:
        """Should return False when smtp_user is empty."""
        config = EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="",
            smtp_pass="secret123",
        )
        assert config.is_valid() is False

    def test_is_valid_returns_false_for_empty_pass(self) -> None:
        """Should return False when smtp_pass is empty."""
        config = EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_pass="",
        )
        assert config.is_valid() is False
