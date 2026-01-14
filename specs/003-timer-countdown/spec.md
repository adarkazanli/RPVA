# Feature Specification: Timer Countdown Announcement

**Feature Branch**: `003-timer-countdown`
**Created**: 2026-01-14
**Status**: Implemented
**Input**: User description: "When a timer is reaching 0, the voice should start counting 5 seconds before, for example, Ammar, you should start your call in 5..4...3..2..1...now. Also, while we want to maintain the friendliness, let us cut out the chat, it is not necessary to be over-friendly."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Countdown Announcement Before Timer Completion (Priority: P1)

As a user, I want the assistant to start a verbal countdown 5 seconds before my timer reaches zero, so that I am prepared for the upcoming task and can transition smoothly without being startled by a sudden reminder.

**Why this priority**: This is the core feature request - the countdown prepares users for imminent tasks and provides a natural transition rather than an abrupt notification.

**Independent Test**: Can be fully tested by setting a 10-second timer and verifying that at 5 seconds remaining, the assistant begins counting down "5..4..3..2..1..now" followed by the task announcement.

**Acceptance Scenarios**:

1. **Given** a timer is set for "start your call" and 5 seconds remain, **When** the countdown begins, **Then** the assistant announces "[Name], you should start your call in 5..4..3..2..1..now."

2. **Given** a timer has less than 5 seconds remaining when set (e.g., 3-second timer), **When** the timer starts, **Then** the countdown begins immediately from the remaining time (e.g., "3..2..1..now").

3. **Given** a timer is set with a specific task description, **When** the countdown begins, **Then** the task is mentioned naturally within the countdown phrase (e.g., "[Name], you should [task] in 5..4..3..2..1..now").

---

### User Story 2 - Personalized Countdown with User's Name (Priority: P2)

As a user, I want the countdown to address me by name, so that I know the reminder is specifically for me and it feels personal.

**Why this priority**: Personalization creates a direct connection with the user and ensures they know they're being addressed, especially in shared environments.

**Independent Test**: Can be tested by setting a timer and verifying the countdown includes the user's name at the beginning of the announcement.

**Acceptance Scenarios**:

1. **Given** the system knows the user's name is "Ammar", **When** a timer countdown begins, **Then** the announcement starts with "Ammar, you should..."

2. **Given** the user's name is not configured, **When** a timer countdown begins, **Then** the assistant uses a friendly generic address (e.g., "Hey, you should...").

---

### User Story 3 - Concise and Friendly Tone Without Excessive Chat (Priority: P3)

As a user, I want the assistant's responses to be friendly but concise, so that I get the information I need without unnecessary verbosity or over-the-top friendliness.

**Why this priority**: Reduces noise and cognitive load while maintaining a pleasant user experience. Users want efficiency with warmth, not lengthy conversations.

**Independent Test**: Can be tested by interacting with the assistant and verifying responses are warm but brief, without multiple sentences of filler or excessive enthusiasm.

**Acceptance Scenarios**:

1. **Given** the user sets a reminder, **When** the assistant confirms, **Then** the confirmation is one clear sentence with the essential information (time and task) without embellishments like "Oh how wonderful!" or "I'd be delighted to help you with that!"

2. **Given** a timer countdown completes, **When** the "now" moment arrives, **Then** there is no lengthy follow-up chatter - just the task announcement.

3. **Given** the user asks to list reminders, **When** the assistant responds, **Then** the list is presented clearly and directly without verbose introductions or excessive pleasantries.

---

### Edge Cases

- **Timer shorter than 5 seconds**: When a timer is set for less than 5 seconds, the countdown starts immediately from the remaining time (e.g., a 3-second timer counts "3..2..1..now").
- **Multiple timers reaching zero simultaneously**: When multiple timers would trigger within the same 5-second countdown window, combine all tasks into a single countdown announcement (e.g., "Ammar, you should start your call and check the oven in 5..4..3..2..1..now").
- **Timer cancelled during countdown**: If a timer is cancelled while the countdown is in progress, the countdown stops immediately and no "now" announcement is made.
- **System load during countdown**: Countdown timing maintains accuracy; each number is spoken at approximately 1-second intervals regardless of system load.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST begin a verbal countdown 5 seconds before any timer reaches zero.
- **FR-002**: System MUST announce each countdown number ("5..4..3..2..1..now") with approximately 1-second intervals.
- **FR-003**: System MUST include the task description naturally within the countdown phrase.
- **FR-004**: System MUST address the user by name at the start of the countdown when the name is configured.
- **FR-005**: System MUST use a friendly generic address when the user's name is not configured.
- **FR-006**: System MUST handle timers shorter than 5 seconds by starting the countdown from the remaining time.
- **FR-007**: System MUST stop the countdown immediately if a timer is cancelled mid-countdown.
- **FR-008**: System MUST maintain a concise, friendly tone in all responses without excessive verbosity.
- **FR-009**: System MUST provide confirmation messages in one clear sentence containing essential information only.
- **FR-010**: System MUST avoid filler phrases, excessive enthusiasm, or unnecessary pleasantries in responses.
- **FR-011**: System MUST combine multiple tasks into a single countdown announcement when timers trigger within the same 5-second countdown window.

### Key Entities

- **Timer Countdown**: A 5-second (or less) verbal announcement sequence that precedes timer completion, consisting of numbered intervals and the task description.
- **User Profile**: Contains the user's name for personalized announcements; may be empty/unconfigured.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of timers trigger a countdown announcement starting at 5 seconds (or from remaining time if less than 5 seconds).
- **SC-002**: Countdown numbers are announced at 1-second intervals with less than 200ms variance.
- **SC-003**: Users recognize their name in the countdown announcement 100% of the time when configured.
- **SC-004**: Average response length for confirmations is reduced by 50% compared to previous verbose style.
- **SC-005**: Users can complete their prompted task within 2 seconds of hearing "now" due to adequate preparation time.
- **SC-006**: 90% of users describe the assistant's tone as "friendly but efficient" in feedback.

## Clarifications

### Session 2026-01-14

- Q: How should the system handle multiple timers reaching zero simultaneously? → A: Combine both tasks in a single countdown announcement

## Assumptions

- The existing timer/reminder system from 002-personality-timers is fully functional and this feature builds upon it.
- The speech synthesis/output system can handle real-time countdown delivery with consistent timing.
- User name configuration exists or can be added to user preferences.
- The wake word "Purcobine" (or configured name) remains unchanged from the existing system.
