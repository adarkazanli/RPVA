# Data Model: Email Action Items

**Feature**: 007-email-action-items
**Date**: 2026-01-14

## Entities

### EmailConfig

Configuration for SMTP email sending, loaded from environment variables.

| Field | Type | Required | Source | Description |
|-------|------|----------|--------|-------------|
| recipient_address | str | Yes | EMAIL_ADDRESS | Email address to send action items to |
| smtp_host | str | Yes | SMTP_HOST | SMTP server hostname |
| smtp_port | int | No | SMTP_PORT | SMTP server port (default: 587) |
| smtp_user | str | Yes | SMTP_USER | SMTP authentication username |
| smtp_pass | str | Yes | SMTP_PASS | SMTP authentication password |

**Validation Rules**:
- `recipient_address` must be a valid email format
- `smtp_host` must be non-empty
- `smtp_port` must be 1-65535 (default 587 if not set)
- `smtp_user` and `smtp_pass` must be non-empty

**States**:
- `valid` - All required fields present and valid
- `invalid` - Missing or malformed fields
- `unconfigured` - No email settings in environment

### ActionItemEmail

Represents an email message containing action items.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| recipient | str | Yes | Target email address |
| subject | str | Yes | Email subject line with date |
| body | str | Yes | Formatted action items list |
| date_ref | date | Yes | Date of action items (today/yesterday) |
| item_count | int | Yes | Number of action items included |
| created_at | datetime | Yes | Timestamp when email was constructed |

**Validation Rules**:
- `item_count` must be > 0 (don't send empty emails)
- `subject` format: "Action Items for {date}"
- `body` must include all action items as bullet list

## Relationships

```
EmailConfig (1) ----uses----> (many) ActionItemEmail
                                      |
                                      |
                                      v
                              MongoDB notes collection
                              (existing, read-only)
```

## Data Flow

1. User says "email me my action items"
2. System loads `EmailConfig` from environment
3. System queries existing `notes` collection for action items
4. System constructs `ActionItemEmail` with formatted content
5. System sends via SMTP using `EmailConfig` credentials
6. System confirms success/failure verbally

## No Persistence Required

This feature does not persist new data. It:
- Reads from existing `notes` collection (action_items field)
- Reads configuration from environment variables
- Sends transient email messages

No database migrations or new collections needed.
