# Internal Contract: Email Service

**Feature**: 007-email-action-items
**Date**: 2026-01-14

## Overview

Internal service contract for the email module. This is not an external API - it defines the interface between the orchestrator and the email service.

## EmailConfig Interface

```python
@dataclass
class EmailConfig:
    """SMTP configuration loaded from environment."""

    recipient_address: str
    smtp_host: str
    smtp_port: int  # default: 587
    smtp_user: str
    smtp_pass: str

    @classmethod
    def from_env(cls) -> "EmailConfig | None":
        """Load config from environment variables.

        Returns:
            EmailConfig if all required vars present, None otherwise.
        """
        ...

    def is_valid(self) -> bool:
        """Check if configuration is complete and valid."""
        ...
```

## EmailSender Interface

```python
class EmailSender(Protocol):
    """Protocol for sending emails."""

    def send_action_items(
        self,
        action_items: list[str],
        date_label: str,  # "today" or "yesterday"
        target_date: date,
    ) -> EmailResult:
        """Send action items email.

        Args:
            action_items: List of action item strings
            date_label: Human-readable date reference
            target_date: Actual date for subject line

        Returns:
            EmailResult with success/failure status
        """
        ...
```

## EmailResult Interface

```python
@dataclass
class EmailResult:
    """Result of email send operation."""

    success: bool
    error_message: str | None = None

    # Predefined results
    @classmethod
    def ok(cls) -> "EmailResult":
        return cls(success=True)

    @classmethod
    def not_configured(cls) -> "EmailResult":
        return cls(success=False, error_message="Email is not configured.")

    @classmethod
    def no_items(cls) -> "EmailResult":
        return cls(success=False, error_message="No action items to send.")

    @classmethod
    def auth_failed(cls) -> "EmailResult":
        return cls(success=False, error_message="Could not authenticate with email server.")

    @classmethod
    def connection_failed(cls) -> "EmailResult":
        return cls(success=False, error_message="Could not connect to email server.")

    @classmethod
    def send_failed(cls) -> "EmailResult":
        return cls(success=False, error_message="Failed to send email.")
```

## Orchestrator Integration

```python
# In orchestrator.py

def _handle_email_action_items(self, intent: Intent) -> str:
    """Handle email action items intent.

    Intent patterns:
    - "email me my action items"
    - "send my action items to my email"
    - "email me yesterday's action items"

    Returns:
        Verbal response confirming success or explaining failure.
    """
    ...
```

## Intent Patterns

New intent type: `EMAIL_ACTION_ITEMS`

Patterns to match:
- `email (?:me )?(?:my )?action items`
- `send (?:my )?action items (?:to )?(?:my )?email`
- `email (?:me )?(?:my )?action items (?:from |for )?(today|yesterday)`

Entity extraction:
- `date_ref`: "today" (default) or "yesterday"

## Error Response Mapping

| EmailResult | Verbal Response |
|-------------|-----------------|
| ok() | "Done! I've sent your action items to your email." |
| not_configured() | "Email is not configured. Please set up your email settings in the configuration file." |
| no_items() | "You don't have any action items to send." |
| auth_failed() | "I couldn't authenticate with the email server. Please check your email credentials." |
| connection_failed() | "I couldn't connect to the email server. Please check your internet connection and try again." |
| send_failed() | "I wasn't able to send the email. Please try again later." |
