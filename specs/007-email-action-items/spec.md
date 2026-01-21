# Feature Specification: Email Action Items

**Feature Branch**: `007-email-action-items`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "let us introduce the action item of send my action items via email. This should be a simple list to the default email in .env with the variable name EMAIL_ADDRESS"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send Action Items via Voice Command (Priority: P1)

As a user, I want to ask Ara to email me my action items so that I have a written record in my inbox that I can reference later without needing the voice assistant.

**Why this priority**: This is the core feature - enabling users to receive their action items via email with a simple voice command. It provides immediate value by bridging the voice assistant with email for persistent reference.

**Independent Test**: Can be fully tested by saying "email me my action items" and verifying an email is received at the configured address with the correct list of action items.

**Acceptance Scenarios**:

1. **Given** I have action items recorded for today, **When** I say "email me my action items", **Then** an email is sent to my configured email address containing a list of all today's action items.

2. **Given** I have no action items recorded for today, **When** I say "email me my action items", **Then** Ara responds verbally that there are no action items to send.

3. **Given** I have action items recorded, **When** I say "send my action items to my email", **Then** the system recognizes this as an email request and sends the email.

---

### User Story 2 - Email Yesterday's Action Items (Priority: P2)

As a user, I want to email myself action items from yesterday so that I can review and follow up on items I may have missed.

**Why this priority**: Extends the core functionality to support historical queries, which users will naturally want after using the primary feature.

**Independent Test**: Can be tested by saying "email me my action items from yesterday" and verifying the email contains only yesterday's items.

**Acceptance Scenarios**:

1. **Given** I have action items from yesterday, **When** I say "email me yesterday's action items", **Then** an email is sent containing only yesterday's action items.

2. **Given** I have no action items from yesterday, **When** I say "email me yesterday's action items", **Then** Ara responds that there are no action items from yesterday to send.

---

### Edge Cases

- What happens when the email address is not configured in the environment? System should respond with a helpful message that email is not configured.
- What happens when SMTP credentials are missing or invalid? System should respond that email cannot be sent due to configuration issues.
- What happens when the email service is unavailable? System should inform the user that the email could not be sent and suggest trying again later.
- What happens when the action items list is very long? Email should include all items regardless of count.
- What happens when action items contain special characters? Email should display them correctly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST send an email containing action items when user requests via voice command
- **FR-002**: System MUST read the recipient email address from the EMAIL_ADDRESS environment variable
- **FR-003**: System MUST recognize voice commands such as "email me my action items", "send my action items to my email", and similar variations
- **FR-004**: System MUST format action items as a simple readable list in the email body
- **FR-005**: System MUST support sending action items for "today" (default) or "yesterday"
- **FR-006**: System MUST provide verbal confirmation when email is successfully sent
- **FR-007**: System MUST provide verbal feedback when email cannot be sent (no items, not configured, service error)
- **FR-008**: System MUST include a clear subject line indicating the email contains action items and the date

### Key Entities

- **ActionItemEmail**: Represents an outgoing email containing action items; includes recipient address, subject line, body with formatted action item list, and send timestamp
- **EmailConfiguration**: SMTP settings from environment variables: EMAIL_ADDRESS (recipient), SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can trigger email delivery with a single voice command in under 5 seconds
- **SC-002**: Email arrives in user's inbox within 30 seconds of voice command
- **SC-003**: 100% of recorded action items for the requested date appear in the email
- **SC-004**: Users receive clear verbal feedback for all outcomes (sent, no items, error) within 3 seconds

## Assumptions

- Email delivery uses SMTP with user-provided credentials (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS environment variables)
- The email will be sent as plain text for simplicity
- The system already has the capability to query action items (implemented in previous features)
- Users have access to configure the .env file or it will be pre-configured during setup

## Clarifications

### Session 2026-01-14

- Q: Email delivery method? → A: SMTP with user-provided credentials (SMTP_HOST, SMTP_USER, SMTP_PASS in .env)
