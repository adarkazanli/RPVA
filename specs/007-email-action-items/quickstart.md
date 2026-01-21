# Quickstart: Email Action Items

**Feature**: 007-email-action-items
**Date**: 2026-01-14

## Prerequisites

1. Ara voice assistant running
2. Action items already recorded (via "take note" commands)
3. Email credentials configured in `.env`

## Configuration

Add the following to your `.env` file:

```bash
# Email recipient (where action items will be sent)
EMAIL_ADDRESS=your-email@example.com

# SMTP server settings
SMTP_HOST=smtp.gmail.com    # or your email provider's SMTP server
SMTP_PORT=587               # Standard STARTTLS port
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password # Use app-specific password for Gmail
```

### Gmail Setup

1. Enable 2-Factor Authentication on your Google account
2. Go to Google Account → Security → App passwords
3. Generate a new app password for "Mail"
4. Use this app password as `SMTP_PASS`

### Outlook/Microsoft Setup

1. Use `smtp.office365.com` as SMTP_HOST
2. Use your full email as SMTP_USER
3. Use your account password or app password

## Test Scenarios

### Scenario 1: Email Today's Action Items

**Setup**: Create some action items first
```
"Ara, take note: I need to call John about the project"
"Ara, take note: Review the quarterly report"
```

**Test**:
```
"Ara, email me my action items"
```

**Expected**:
- Ara says: "Done! I've sent your action items to your email."
- Email arrives with subject: "Action Items for January 14, 2026"
- Email body contains both action items as bullets

### Scenario 2: Email Yesterday's Action Items

**Test**:
```
"Ara, email me yesterday's action items"
```

**Expected** (if items exist):
- Email arrives with yesterday's date in subject
- Only yesterday's items included

**Expected** (if no items):
- Ara says: "You don't have any action items from yesterday to send."

### Scenario 3: No Email Configuration

**Setup**: Remove or comment out EMAIL_ADDRESS from `.env`

**Test**:
```
"Ara, email me my action items"
```

**Expected**:
- Ara says: "Email is not configured. Please set up your email settings in the configuration file."

### Scenario 4: No Action Items

**Setup**: Ensure no notes with action items exist for today

**Test**:
```
"Ara, email me my action items"
```

**Expected**:
- Ara says: "You don't have any action items to send."

## Voice Command Variations

All of these should work:
- "Email me my action items"
- "Send my action items to my email"
- "Email my action items"
- "Send action items to email"
- "Email me my action items for today"
- "Email me yesterday's action items"
- "Email me my action items from yesterday"

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Email is not configured" | Check `.env` has EMAIL_ADDRESS set |
| "Could not authenticate" | Verify SMTP_USER and SMTP_PASS; use app password for Gmail |
| "Could not connect" | Check SMTP_HOST and SMTP_PORT; verify internet connection |
| Email not arriving | Check spam folder; verify EMAIL_ADDRESS is correct |
