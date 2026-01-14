# Feature Specification: Warm Personality with Timer/Reminder System

**Feature Branch**: `002-personality-timers`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Replace the current personality with a warm, playful and witty personality. The agent must be aware of the time and should be able to handle timers. For example, I want to say Purcobine, remind me in five minutes to do this. It should confirm the reminder to say assuming now it is 2:34am, I will remind you at 2:39am to do the task. She should be able to handle multiple tasks at the same time. I should be able to ask her to list all current timers and she should be able to list them for me."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Set a Reminder with Voice Command (Priority: P1)

As a user, I want to ask Purcobine to remind me of something after a specified duration so that I don't have to remember tasks myself. The assistant should respond with warmth and wit while confirming the exact time the reminder will trigger.

**Why this priority**: This is the core functionality - without the ability to set timers/reminders, the other features (listing, personality) have no purpose.

**Independent Test**: Can be fully tested by saying "Purcobine, remind me in 5 minutes to check the oven" and verifying the assistant confirms with the calculated target time, then delivers the reminder at the correct time.

**Acceptance Scenarios**:

1. **Given** the current time is 2:34 AM, **When** the user says "Purcobine, remind me in five minutes to check the oven", **Then** the assistant responds with a warm confirmation including both the current time context and the calculated reminder time (2:39 AM), and the task description.

2. **Given** a reminder has been set, **When** the reminder time arrives, **Then** the assistant notifies the user of the task in a warm, engaging manner.

3. **Given** the user provides a reminder request, **When** the time duration is ambiguous (e.g., "in a bit"), **Then** the assistant asks for clarification with a playful tone.

---

### User Story 2 - Manage Multiple Concurrent Reminders (Priority: P2)

As a user, I want to set multiple reminders at the same time so that I can track several tasks without one overwriting another.

**Why this priority**: Users commonly need to track multiple things simultaneously - this enables practical daily use of the reminder feature.

**Independent Test**: Can be tested by setting 3 different reminders in sequence and verifying all three trigger at their respective times.

**Acceptance Scenarios**:

1. **Given** a reminder is already active for 5 minutes, **When** the user sets another reminder for 10 minutes, **Then** both reminders are tracked independently and will trigger at their respective times.

2. **Given** multiple reminders are active, **When** two reminders are scheduled to trigger at the same time, **Then** the assistant delivers both reminders clearly, distinguishing between tasks.

3. **Given** multiple reminders are active, **When** one reminder triggers, **Then** the other reminders remain unaffected and continue counting down.

---

### User Story 3 - List Active Reminders with Numbered Format (Priority: P3)

As a user, I want to ask Purcobine to list all my current reminders in a numbered format so that I can see what reminders are pending and easily reference them by number for deletion.

**Why this priority**: This provides visibility into the reminder system and enables users to manage reminders by number.

**Independent Test**: Can be tested by setting 2-3 reminders, then asking "What reminders do I have?" and verifying all are listed with ordinal numbers (first, second, third), target times, and tasks.

**Acceptance Scenarios**:

1. **Given** multiple reminders are active, **When** the user asks "What reminders do I have?" or "List my timers", **Then** the assistant lists all active reminders in numbered format: "First, you have a reminder at 3:18 AM to check the oven. Second, you have a reminder at 3:25 AM to call Mom."

2. **Given** no reminders are active, **When** the user asks to list reminders, **Then** the assistant responds warmly that there are no active reminders.

3. **Given** reminders are listed, **When** the user views the list, **Then** reminders are presented in chronological order by trigger time with ordinal numbering (first, second, third, etc.).

---

### User Story 4 - Warm, Playful, and Witty Personality (Priority: P4)

As a user, I want Purcobine to have a warm, playful, and witty personality so that interactions feel engaging and personable rather than robotic.

**Why this priority**: Personality enhances user experience but the core timer functionality must work first. This can be layered onto the existing features.

**Independent Test**: Can be tested by having any conversation with Purcobine and evaluating that responses include warmth (friendly tone), playfulness (light humor, casual language), and wit (clever phrasing, occasional puns).

**Acceptance Scenarios**:

1. **Given** the user interacts with Purcobine, **When** Purcobine responds to any request, **Then** the response demonstrates warmth through friendly, caring language.

2. **Given** the user sets a reminder, **When** Purcobine confirms the reminder, **Then** the confirmation includes a playful or witty element while remaining informative.

3. **Given** the user makes a mistake or unclear request, **When** Purcobine asks for clarification, **Then** the response is gentle and encouraging, not cold or judgmental.

---

### User Story 5 - Cancel Reminders by Description or Number (Priority: P5)

As a user, I want to be able to cancel specific reminders by description, by number (from the list), or multiple reminders at once so that I can efficiently manage my reminders when plans change.

**Why this priority**: Natural extension of reminder management - users will inevitably need to cancel reminders they no longer need, and numbered references make this faster.

**Independent Test**: Can be tested by setting multiple reminders, listing them, then canceling "reminder number 3" and verifying only that specific reminder is removed.

**Acceptance Scenarios**:

1. **Given** a reminder is active for "check the oven", **When** the user says "Cancel my reminder about the oven", **Then** the assistant confirms cancellation and the reminder is removed.

2. **Given** multiple reminders are listed (first, second, third...), **When** the user says "Delete reminder number 3" or "Cancel the third reminder", **Then** the assistant cancels the third reminder in the list and confirms which one was removed.

3. **Given** multiple reminders are listed, **When** the user says "Delete the third and sixth reminders" or "Cancel reminders 2, 4, and 5", **Then** the assistant cancels all specified reminders and confirms which ones were removed.

4. **Given** the user specifies an invalid reminder number (e.g., "delete reminder 10" when only 5 exist), **When** the number is out of range, **Then** the assistant responds warmly that no reminder with that number exists and offers to list current reminders.

5. **Given** multiple similar reminders exist, **When** the user tries to cancel ambiguously by description, **Then** the assistant asks for clarification or suggests using the numbered list.

---

### User Story 6 - Clear All Reminders (Priority: P6)

As a user, I want to be able to clear all reminders at once so that I can quickly start fresh without canceling each reminder individually.

**Why this priority**: Convenience feature for bulk management - useful when plans change significantly or for testing/reset scenarios.

**Independent Test**: Can be tested by setting 5 reminders, saying "clear all reminders", and verifying all reminders are removed and none trigger.

**Acceptance Scenarios**:

1. **Given** multiple reminders are active, **When** the user says "Clear all reminders" or "Delete all my reminders", **Then** the assistant confirms by stating how many reminders were cleared (e.g., "Done! I've cleared all 5 of your reminders.").

2. **Given** no reminders are active, **When** the user asks to clear all reminders, **Then** the assistant responds warmly that there are no reminders to clear.

3. **Given** the user requests to clear all reminders, **When** the action completes, **Then** the persistence file is updated to reflect the empty state.

---

### Edge Cases

- **Zero/negative duration**: When the user sets a reminder for zero or negative time (e.g., "remind me 0 minutes ago"), the system gracefully rejects the request with a warm message: "Hmm, I can't set a reminder for the past! How about a few minutes from now?"
- **Very long durations**: Accepted without limit (e.g., "remind me in 24 hours" or longer). User is not warned about persistence since reminders survive restarts.
- **Restart recovery**: Reminders persist to storage and are automatically restored when the assistant restarts. Any reminders whose trigger time passed during downtime are delivered immediately upon restart with an explanation.
- **Time zone handling**: All times are stored in UTC and displayed in the system's local timezone. If a user mentions a specific timezone, the system asks for clarification: "I work with your local time - do you mean X:XX in your current timezone?"
- **Missing task description**: When the user sets a reminder without specifying what to remind them about, the system asks for clarification: "What would you like me to remind you about?"

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to set reminders via voice command specifying a duration (e.g., "in 5 minutes") and a task description.
- **FR-002**: System MUST confirm reminders by stating the current time and the calculated target trigger time.
- **FR-003**: System MUST support multiple concurrent active reminders without limit.
- **FR-004**: System MUST trigger reminder notifications at the specified times.
- **FR-005**: System MUST allow users to list all active reminders with their target times and task descriptions in numbered format (first, second, third, etc.).
- **FR-006**: System MUST allow users to cancel specific reminders by description, time reference, or by number from the list.
- **FR-015**: System MUST allow users to cancel multiple reminders at once by specifying multiple numbers (e.g., "delete reminders 2, 4, and 5").
- **FR-016**: System MUST allow users to clear all reminders at once with a single command.
- **FR-017**: System MUST maintain consistent numbering of reminders in chronological order when listing.
- **FR-007**: System MUST persist active reminders to storage so they survive system restarts and are automatically restored.
- **FR-008**: System MUST be aware of the current time and able to communicate it accurately.
- **FR-009**: System MUST respond with a warm, playful, and witty personality in all interactions.
- **FR-010**: System MUST use friendly, engaging language rather than robotic or formal responses.
- **FR-011**: System MUST handle ambiguous time requests by asking for clarification.
- **FR-012**: System MUST reject requests for reminders with zero or negative durations gracefully.
- **FR-013**: System MUST accept reminders of any duration without maximum limit.
- **FR-014**: System MUST deliver any missed reminders (whose trigger time passed during system downtime) immediately upon restart.

### Key Entities

- **Reminder**: Represents a scheduled notification with a target trigger time, task description, creation time, and unique identifier.
- **Personality Profile**: Defines the assistant's communication style including warmth indicators, wit patterns, and playfulness guidelines.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can set a reminder and receive confirmation within 2 seconds of the voice command.
- **SC-002**: 100% of properly set reminders trigger within 5 seconds of their target time.
- **SC-003**: Users can successfully manage 10+ concurrent reminders without confusion or system degradation.
- **SC-004**: Users rate the assistant's personality as "warm" or "friendly" in 80%+ of feedback responses. *(Manual QA assessment during user testing)*
- **SC-005**: Users can list all active reminders and receive a complete, accurate list within 2 seconds.
- **SC-006**: Users successfully cancel reminders on first attempt 90%+ of the time when providing clear identification.
- **SC-007**: Users can cancel reminders by number reference 100% of the time when providing valid numbers.
- **SC-008**: Users can clear all reminders and receive confirmation within 2 seconds.

## Clarifications

### Session 2026-01-14

- Q: What is the maximum reminder duration? → A: No limit - accept any duration the user specifies
- Q: How should reminders behave after system restart? → A: Persist to file - reminders survive restarts and are restored automatically

## Assumptions

- The assistant (Purcobine) already exists as a functional voice assistant that can receive and process voice commands.
- The system has access to accurate system time.
- "Purcobine" is the wake word already configured for the assistant.
- Audio notification/speech output capability already exists for delivering reminders.
- Reminders are persisted to local storage and survive system restarts.
