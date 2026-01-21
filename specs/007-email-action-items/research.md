# Research: Email Action Items

**Feature**: 007-email-action-items
**Date**: 2026-01-14

## Research Questions

### 1. Python SMTP Best Practices

**Decision**: Use `smtplib` with `email.mime` from Python standard library

**Rationale**:
- No external dependencies required (aligns with YAGNI principle)
- Well-documented, stable API
- Supports TLS/SSL for secure connections
- Works with all major email providers (Gmail, Outlook, etc.)

**Alternatives Considered**:
- `yagmail` - Simpler API but adds dependency
- `sendgrid` SDK - Requires external service account
- `boto3` SES - AWS-specific, adds complexity

**Implementation Pattern**:
```python
import smtplib
from email.mime.text import MIMEText

with smtplib.SMTP(host, port) as server:
    server.starttls()  # Upgrade to TLS
    server.login(user, password)
    server.send_message(msg)
```

### 2. SMTP Port Configuration

**Decision**: Default to port 587 (STARTTLS), configurable via SMTP_PORT

**Rationale**:
- Port 587 is the standard submission port with STARTTLS
- Works with Gmail, Outlook, most ISPs
- More firewall-friendly than port 465 (implicit TLS)

**Alternatives Considered**:
- Port 465 (SMTPS/implicit TLS) - Less universally supported
- Port 25 (plain SMTP) - Often blocked, insecure

### 3. Error Handling Strategy

**Decision**: Catch specific SMTP exceptions, return user-friendly messages

**Rationale**:
- Users need clear feedback on what went wrong
- Don't expose technical details (security)
- Allow retry for transient failures

**Error Categories**:
| Error Type | User Message |
|------------|--------------|
| Missing config | "Email is not configured. Please set up your email settings." |
| Auth failure | "Could not authenticate with email server. Please check your credentials." |
| Connection error | "Could not connect to email server. Please try again later." |
| Send failure | "Failed to send email. Please try again." |

### 4. Email Content Format

**Decision**: Plain text with simple bullet list format

**Rationale**:
- Maximum compatibility across email clients
- Faster to generate (no HTML templating)
- Easier to read on mobile devices
- Aligns with simplicity principle

**Format**:
```
Subject: Action Items for January 14, 2026

Your action items for today:

• Send email to R.C. Johnson
• Review quarterly report
• Schedule dentist appointment

---
Sent by Ara Voice Assistant
```

### 5. Async vs Sync Email Sending

**Decision**: Synchronous send with timeout, verbal response after completion

**Rationale**:
- Simpler implementation (no threading complexity)
- Email send is fast (<5 seconds typically)
- User wants confirmation that email was sent
- Can always add async later if needed (YAGNI)

**Alternatives Considered**:
- Background thread - Adds complexity, harder to report errors
- asyncio - Requires async refactor of orchestrator

## Resolved Unknowns

All technical questions resolved. No NEEDS CLARIFICATION items remain.

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| smtplib | stdlib | SMTP client |
| email.mime | stdlib | Email message construction |
| ssl | stdlib | TLS support |

No new external dependencies required.
