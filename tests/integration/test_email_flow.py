"""Integration tests for email action items flow."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from ara.email.config import EmailConfig
from ara.email.sender import EmailResult, SMTPEmailSender


class TestEmailSendFlow:
    """Integration tests for email send flow with mock SMTP (US1: T012)."""

    @pytest.fixture
    def valid_config(self) -> EmailConfig:
        """Create a valid email configuration."""
        return EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )

    @pytest.fixture
    def email_sender(self, valid_config: EmailConfig) -> SMTPEmailSender:
        """Create an email sender with valid config."""
        return SMTPEmailSender(valid_config)

    def test_send_action_items_success_with_mock_smtp(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Should successfully send email when SMTP mock succeeds."""
        items = ["Call John", "Review report"]
        target_date = date.today()

        with patch("ara.email.sender.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp

            result = email_sender.send_action_items(items, "today", target_date)

        assert result.success is True
        assert result.error_message is None
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    def test_send_action_items_includes_all_items_in_body(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Email body should contain all action items."""
        items = ["Task A", "Task B", "Task C"]
        target_date = date.today()

        with patch("ara.email.sender.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp

            email_sender.send_action_items(items, "today", target_date)

            # Get the message that was sent
            call_args = mock_smtp.send_message.call_args
            sent_message = call_args[0][0]
            body = sent_message.get_payload(decode=True).decode("utf-8")

            assert "Task A" in body
            assert "Task B" in body
            assert "Task C" in body

    def test_send_action_items_returns_no_items_when_empty_list(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Should return no_items result when action items list is empty."""
        result = email_sender.send_action_items([], "today", date.today())

        assert result.success is False
        assert result.error_message == "No action items to send."

    def test_send_action_items_auth_failure_returns_auth_failed(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Should return auth_failed when SMTP authentication fails."""
        import smtplib

        items = ["Task one"]
        target_date = date.today()

        with patch("ara.email.sender.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp
            mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(
                535, b"Authentication failed"
            )

            result = email_sender.send_action_items(items, "today", target_date)

        assert result.success is False
        assert "authenticate" in result.error_message.lower()

    def test_send_action_items_connection_failure_returns_connection_failed(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Should return connection_failed when SMTP connection fails."""
        items = ["Task one"]
        target_date = date.today()

        with patch("ara.email.sender.smtplib.SMTP") as mock_smtp_class:
            mock_smtp_class.side_effect = OSError("Connection refused")

            result = email_sender.send_action_items(items, "today", target_date)

        assert result.success is False
        assert "connect" in result.error_message.lower()


class TestYesterdayEmailFlow:
    """Integration tests for yesterday's action items email (US2: T022)."""

    @pytest.fixture
    def valid_config(self) -> EmailConfig:
        """Create a valid email configuration."""
        return EmailConfig(
            recipient_address="test@example.com",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_pass="secret123",
        )

    @pytest.fixture
    def email_sender(self, valid_config: EmailConfig) -> SMTPEmailSender:
        """Create an email sender with valid config."""
        return SMTPEmailSender(valid_config)

    def test_send_yesterday_items_uses_correct_subject(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Email subject should reflect yesterday's date."""
        items = ["Follow up task"]
        yesterday = date.today() - timedelta(days=1)

        with patch("ara.email.sender.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp

            email_sender.send_action_items(items, "yesterday", yesterday)

            call_args = mock_smtp.send_message.call_args
            sent_message = call_args[0][0]
            subject = sent_message["Subject"]

            # Subject should contain yesterday's date
            expected_date = yesterday.strftime("%B %d, %Y")
            assert expected_date in subject

    def test_send_yesterday_items_body_references_yesterday(
        self, email_sender: SMTPEmailSender
    ) -> None:
        """Email body should reference 'yesterday'."""
        items = ["Follow up task"]
        yesterday = date.today() - timedelta(days=1)

        with patch("ara.email.sender.smtplib.SMTP") as mock_smtp_class:
            mock_smtp = MagicMock()
            mock_smtp_class.return_value.__enter__.return_value = mock_smtp

            email_sender.send_action_items(items, "yesterday", yesterday)

            call_args = mock_smtp.send_message.call_args
            sent_message = call_args[0][0]
            body = sent_message.get_payload(decode=True).decode("utf-8")

            assert "yesterday" in body.lower()
