"""Email sender for action items via SMTP."""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import EmailConfig

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Result of email send operation."""

    success: bool
    error_message: str | None = None

    @classmethod
    def ok(cls) -> EmailResult:
        """Create success result."""
        return cls(success=True)

    @classmethod
    def not_configured(cls) -> EmailResult:
        """Create failure result for missing configuration."""
        return cls(success=False, error_message="Email is not configured.")

    @classmethod
    def no_items(cls) -> EmailResult:
        """Create failure result for no action items."""
        return cls(success=False, error_message="No action items to send.")

    @classmethod
    def auth_failed(cls) -> EmailResult:
        """Create failure result for authentication error."""
        return cls(success=False, error_message="Could not authenticate with email server.")

    @classmethod
    def connection_failed(cls) -> EmailResult:
        """Create failure result for connection error."""
        return cls(success=False, error_message="Could not connect to email server.")

    @classmethod
    def send_failed(cls) -> EmailResult:
        """Create failure result for send error."""
        return cls(success=False, error_message="Failed to send email.")


class SMTPEmailSender:
    """Sends emails via SMTP."""

    def __init__(self, config: EmailConfig) -> None:
        """Initialize with email configuration.

        Args:
            config: SMTP configuration from environment.
        """
        self._config = config

    def send_action_items(
        self,
        action_items: list[str],
        date_label: str,
        target_date: date,
    ) -> EmailResult:
        """Send action items email.

        Args:
            action_items: List of action item strings.
            date_label: Human-readable date reference ("today" or "yesterday").
            target_date: Actual date for subject line.

        Returns:
            EmailResult with success/failure status.
        """
        if not action_items:
            return EmailResult.no_items()

        if not self._config.is_valid():
            return EmailResult.not_configured()

        # Format email content
        subject = self._format_subject(target_date)
        body = self._format_email_body(action_items, date_label)

        # Create message
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._config.smtp_user
        msg["To"] = self._config.recipient_address

        # Send email
        try:
            logger.info(
                f"Sending action items email to {self._config.recipient_address}"
            )
            context = ssl.create_default_context()

            with smtplib.SMTP(
                self._config.smtp_host,
                self._config.smtp_port,
                timeout=30,
            ) as server:
                server.starttls(context=context)
                server.login(self._config.smtp_user, self._config.smtp_pass)
                server.send_message(msg)

            logger.info("Email sent successfully")
            return EmailResult.ok()

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return EmailResult.auth_failed()

        except (smtplib.SMTPConnectError, OSError, TimeoutError) as e:
            logger.error(f"SMTP connection failed: {e}")
            return EmailResult.connection_failed()

        except smtplib.SMTPException as e:
            logger.error(f"SMTP send failed: {e}")
            return EmailResult.send_failed()

    @staticmethod
    def _format_subject(target_date: date) -> str:
        """Format email subject line.

        Args:
            target_date: Date for the subject.

        Returns:
            Formatted subject line.
        """
        date_str = target_date.strftime("%B %d, %Y")
        return f"Action Items for {date_str}"

    @staticmethod
    def _format_email_body(action_items: list[str], date_label: str) -> str:
        """Format email body with action items as bullet list.

        Args:
            action_items: List of action item strings.
            date_label: "today" or "yesterday".

        Returns:
            Formatted email body.
        """
        header = f"Your action items for {date_label}:\n\n"

        items_text = "\n".join(f"• {item}" for item in action_items)

        footer = "\n\n---\nSent by Ara Voice Assistant"

        return header + items_text + footer
