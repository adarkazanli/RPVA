"""Unit tests for EmailResult and SMTPEmailSender."""

from datetime import date

import pytest

from ara.email.sender import EmailResult


class TestEmailResultFactoryMethods:
    """Tests for EmailResult factory methods."""

    def test_ok_returns_success_result(self) -> None:
        """EmailResult.ok() should return success with no error."""
        result = EmailResult.ok()
        assert result.success is True
        assert result.error_message is None

    def test_not_configured_returns_failure_with_message(self) -> None:
        """EmailResult.not_configured() should return failure with config message."""
        result = EmailResult.not_configured()
        assert result.success is False
        assert result.error_message == "Email is not configured."

    def test_no_items_returns_failure_with_message(self) -> None:
        """EmailResult.no_items() should return failure with no items message."""
        result = EmailResult.no_items()
        assert result.success is False
        assert result.error_message == "No action items to send."

    def test_auth_failed_returns_failure_with_message(self) -> None:
        """EmailResult.auth_failed() should return failure with auth message."""
        result = EmailResult.auth_failed()
        assert result.success is False
        assert result.error_message == "Could not authenticate with email server."

    def test_connection_failed_returns_failure_with_message(self) -> None:
        """EmailResult.connection_failed() should return failure with connection message."""
        result = EmailResult.connection_failed()
        assert result.success is False
        assert result.error_message == "Could not connect to email server."

    def test_send_failed_returns_failure_with_message(self) -> None:
        """EmailResult.send_failed() should return failure with send message."""
        result = EmailResult.send_failed()
        assert result.success is False
        assert result.error_message == "Failed to send email."


class TestEmailBodyFormatting:
    """Tests for email body formatting (US1: T010)."""

    def test_format_email_body_creates_bullet_list(self) -> None:
        """Email body should format action items as bullet list."""
        from ara.email.sender import SMTPEmailSender

        items = ["Call John", "Review report", "Send invoice"]
        body = SMTPEmailSender._format_email_body(items, "today")

        assert "• Call John" in body
        assert "• Review report" in body
        assert "• Send invoice" in body

    def test_format_email_body_includes_header(self) -> None:
        """Email body should include header with date reference."""
        from ara.email.sender import SMTPEmailSender

        items = ["Task one"]
        body = SMTPEmailSender._format_email_body(items, "today")

        assert "action items for today" in body.lower()

    def test_format_email_body_includes_footer(self) -> None:
        """Email body should include Ara signature."""
        from ara.email.sender import SMTPEmailSender

        items = ["Task one"]
        body = SMTPEmailSender._format_email_body(items, "today")

        assert "Ara Voice Assistant" in body


class TestEmailSubjectFormatting:
    """Tests for email subject line formatting (US1: T011)."""

    def test_format_subject_includes_date(self) -> None:
        """Subject should include the formatted date."""
        from ara.email.sender import SMTPEmailSender

        target_date = date(2026, 1, 14)
        subject = SMTPEmailSender._format_subject(target_date)

        assert "January 14, 2026" in subject

    def test_format_subject_includes_action_items_label(self) -> None:
        """Subject should indicate it contains action items."""
        from ara.email.sender import SMTPEmailSender

        target_date = date(2026, 1, 14)
        subject = SMTPEmailSender._format_subject(target_date)

        assert "Action Items" in subject


class TestYesterdayDateExtraction:
    """Tests for yesterday date handling (US2: T021)."""

    def test_format_email_body_for_yesterday(self) -> None:
        """Email body should reference 'yesterday' when appropriate."""
        from ara.email.sender import SMTPEmailSender

        items = ["Follow up on meeting"]
        body = SMTPEmailSender._format_email_body(items, "yesterday")

        assert "yesterday" in body.lower()
