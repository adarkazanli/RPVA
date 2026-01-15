"""Email configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class EmailConfig:
    """SMTP configuration loaded from environment variables."""

    recipient_address: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str

    @classmethod
    def from_env(cls) -> EmailConfig | None:
        """Load config from environment variables.

        Required environment variables:
        - EMAIL_ADDRESS: Recipient email address
        - SMTP_HOST: SMTP server hostname
        - SMTP_USER: SMTP authentication username
        - SMTP_PASS: SMTP authentication password

        Optional:
        - SMTP_PORT: SMTP server port (default: 587)

        Returns:
            EmailConfig if all required vars present, None otherwise.
        """
        recipient = os.environ.get("EMAIL_ADDRESS", "").strip()
        host = os.environ.get("SMTP_HOST", "").strip()
        port_str = os.environ.get("SMTP_PORT", "587").strip()
        user = os.environ.get("SMTP_USER", "").strip()
        password = os.environ.get("SMTP_PASS", "").strip()

        # Check required fields
        if not recipient or not host or not user or not password:
            return None

        # Parse port
        try:
            port = int(port_str)
        except ValueError:
            port = 587

        return cls(
            recipient_address=recipient,
            smtp_host=host,
            smtp_port=port,
            smtp_user=user,
            smtp_pass=password,
        )

    def is_valid(self) -> bool:
        """Check if configuration is complete and valid.

        Returns:
            True if all fields are valid, False otherwise.
        """
        if not self.recipient_address:
            return False
        if not self.smtp_host:
            return False
        if not (1 <= self.smtp_port <= 65535):
            return False
        if not self.smtp_user:
            return False
        if not self.smtp_pass:
            return False
        return True
