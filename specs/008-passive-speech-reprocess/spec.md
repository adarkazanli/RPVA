# Feature Specification: Passive Speech Interrupt and Reprocessing

**Feature Branch**: `008-passive-speech-reprocess`
**Created**: 2026-01-17
**Status**: Draft
**Input**: User description: "This agent must be very passive, as soon as I say something while in active mode or within 5 seconds of an active mode, it should interrupt delivery of her answer and continue to add to the input. Reprocess the entire conversation that was given to the agent and then create a new response after all the input in its entirety reprocessed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Append Additional Context During Response (Priority: P1)

A user starts speaking to the agent, and while the agent is delivering its response, the user speaks again to add more context or clarify their intent. The agent immediately stops speaking, appends the new input to the original request, and reprocesses the entire combined input to determine the actual user intent before responding.

**Why this priority**: This is the core feature - the agent's ability to listen and adapt to user input mid-response is the fundamental behavior change being requested.

**Independent Test**: Can be fully tested by speaking to the agent, letting it begin responding, then speaking again with additional context. The agent should stop, combine both inputs, and respond appropriately to the complete request.

**Acceptance Scenarios**:

1. **Given** the agent is actively speaking a response, **When** the user says additional words, **Then** the agent immediately stops speaking and waits for user to finish
2. **Given** the agent has stopped speaking after user interrupt, **When** the user finishes their additional input, **Then** the agent combines original + new input and reprocesses the entire request
3. **Given** "Research BSI" was the original request and agent started explaining BSI, **When** user says "add it to my action items", **Then** the agent interprets the complete intent as "add 'Research BSI' to action items" (not research + add)

---

### User Story 2 - Modify Request with Additional Details (Priority: P1)

A user makes a request and while the agent responds, realizes they need to add location, time, or other qualifiers. The user speaks and the agent incorporates these details into the original request.

**Why this priority**: Equally critical as Story 1 - users frequently realize mid-conversation they forgot details. This prevents frustration of having to repeat the entire request.

**Independent Test**: Say "Research BSI", let agent start responding, then say "in Austin". Agent should understand the complete request is "Research BSI in Austin".

**Acceptance Scenarios**:

1. **Given** user said "Research BSI" and agent is responding, **When** user says "in Austin", **Then** agent reprocesses as "Research BSI in Austin"
2. **Given** user said "Set a reminder" and agent is responding, **When** user says "for tomorrow at 3pm", **Then** agent reprocesses as "Set a reminder for tomorrow at 3pm"
3. **Given** user said "Call John" and agent is responding, **When** user says "on his cell", **Then** agent reprocesses as "Call John on his cell"

---

### User Story 3 - Post-Response Continuation Window (Priority: P2)

Within 5 seconds after the agent finishes speaking, if the user speaks again, the agent should still treat it as a continuation of the previous request and reprocess everything together.

**Why this priority**: Important for natural conversation flow, but secondary to the mid-response interrupt capability since this is a grace period enhancement.

**Independent Test**: Ask the agent something, let it fully respond, then within 5 seconds say additional context. Agent should reprocess the combined input.

**Acceptance Scenarios**:

1. **Given** agent just finished responding (less than 5 seconds ago), **When** user speaks additional context, **Then** agent treats new input as continuation and reprocesses combined request
2. **Given** agent finished responding more than 5 seconds ago, **When** user speaks, **Then** agent treats this as a new independent request
3. **Given** user asks "What's the weather" and agent responds, **When** user says "and tomorrow" within 5 seconds, **Then** agent provides weather for today AND tomorrow

---

### User Story 4 - Change Intent Entirely (Priority: P2)

A user makes a request, but while the agent is responding, changes their mind entirely about what they want. The new input should completely redirect the agent's understanding.

**Why this priority**: Supports natural human conversation where people change their minds, but less common than adding context.

**Independent Test**: Say "Tell me about Python", wait for agent to start, then say "actually, what's on my calendar today". Agent should abandon Python explanation and show calendar.

**Acceptance Scenarios**:

1. **Given** agent is explaining Python, **When** user says "actually, what's on my calendar", **Then** agent stops Python explanation and shows calendar
2. **Given** agent is setting a timer, **When** user says "never mind, cancel that", **Then** agent cancels the pending action
3. **Given** any pending response, **When** user says "stop" or "wait", **Then** agent pauses and waits for clarification

---

### Edge Cases

- What happens when user interrupts multiple times in rapid succession?
  - Agent should accumulate all input until user pauses, then reprocess everything together
- How does the system handle background noise vs intentional speech?
  - Use voice activity detection confidence thresholds; only significant speech triggers interrupt
- What happens if the 5-second window overlaps with the agent starting a new response?
  - The continuation window should close when user initiates any new voice activity
- How does the system handle user saying "go ahead" or "continue" after interrupting?
  - Agent should resume previous response if possible, or ask for clarification if context is lost
- What happens if intent cannot be determined from combined input (contradictory/nonsensical)?
  - Agent asks user for clarification while preserving the accumulated input buffer for context

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST immediately stop audio output when user begins speaking during agent response
- **FR-002**: System MUST maintain a buffer of the original user request during response delivery
- **FR-003**: System MUST append any interrupt speech to the original request buffer
- **FR-004**: System MUST reprocess the combined input (original + interrupts) as a single coherent request
- **FR-005**: System MUST maintain a 5-second continuation window after response completion
- **FR-006**: System MUST support unlimited sequential interrupts within the same request context (no maximum limit)
- **FR-007**: System MUST distinguish between "additive" interrupts (adding context) and "redirective" interrupts (changing intent)
- **FR-008**: System MUST handle keywords like "stop", "wait", "cancel", "never mind" as special interrupt types
- **FR-009**: System MUST provide audio/visual feedback when entering interrupt-listening mode
- **FR-010**: System MUST clear the request buffer and continuation window when starting a fresh conversation (after 5-second window expires with no input)
- **FR-011**: System MUST wait for 2 seconds of silence after user stops speaking before considering the interrupt complete and beginning reprocessing
- **FR-012**: System MUST ask user for clarification when intent cannot be determined from combined input, while preserving the accumulated input buffer

### Key Entities

- **Request Buffer**: Accumulates all user speech within a conversation turn, including original request and all interrupts
- **Continuation Window**: 5-second timer that begins when agent finishes speaking, during which additional input is treated as continuation
- **Interrupt Event**: A detected instance of user speech occurring during agent response or within continuation window
- **Conversation Turn**: The complete cycle from user request through agent response, including all interrupts and reprocessing

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agent stops speaking within 500ms of user beginning to speak during response delivery
- **SC-002**: Combined request reprocessing completes within 2 seconds of user finishing their interrupt
- **SC-003**: 90% of users successfully modify their requests mid-response on first attempt
- **SC-004**: Users can add context to requests without repeating original request in 95% of cases
- **SC-005**: Continuation window accurately distinguishes new requests from continuations 90% of the time
- **SC-006**: User task completion rate improves by 30% compared to interruption-free baseline (users don't have to repeat themselves)

## Clarifications

### Session 2026-01-17

- Q: What is the maximum number of interrupts allowed per conversation turn? → A: Unlimited interrupts within conversation turn
- Q: How long must the user pause before the system considers interrupt complete and begins reprocessing? → A: 2 seconds of silence
- Q: What happens if the system cannot determine intent from combined input? → A: Ask user for clarification while preserving accumulated input

## Assumptions

- The system already has voice activity detection (VAD) capabilities to detect when the user is speaking
- The system has the ability to immediately halt audio output (TTS) mid-delivery
- The underlying language model can handle combined/concatenated input and infer intent from context
- Users will naturally pause briefly between their interrupt phrases (allowing the system to detect end of speech)
- The wake word system will not interfere with interrupt detection during active mode
