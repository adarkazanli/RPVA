"""Email module for sending action items via SMTP."""

from .config import EmailConfig
from .sender import EmailResult, SMTPEmailSender

__all__ = [
    "EmailConfig",
    "EmailResult",
    "SMTPEmailSender",
]
