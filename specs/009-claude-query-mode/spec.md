# Feature Specification: Claude Query Mode

**Feature Branch**: `009-claude-query-mode`
**Created**: 2026-01-21
**Status**: Draft
**Input**: User description: "Add special mode where user asks Ara to 'ask Claude' followed by query, Ara sends request to Claude and reads response. User has Claude Max subscription for authentication. All existing rules apply including 5-second post-answer follow-up window."

## Clarifications

### Session 2026-01-21

- Q: How should Ara handle Claude responses that exceed the 60-second listening limit? → A: Summarize - Instruct Claude to provide concise response (fits 60s spoken)
- Q: How long should Claude conversation history be retained for follow-ups? → A: Until user says "new conversation" or similar explicit command
- Q: What type of audio indicator should play while waiting for Claude's response? → A: Musical loop (short melody that repeats)
- Q: How long should Ara wait for Claude's response before timing out? → A: 30 seconds, then ask "Claude is taking longer, try again?"
- Q: Should Claude queries and responses be logged? → A: Yes, all queries and responses logged to local MongoDB (consistent with existing Ara data storage)
- Q: How should logged queries be organized for retrieval? → A: Queries tagged with distinct type (e.g., "claude_query") to enable time-based summaries ("summarize my Claude conversations today/this week/this month")

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Claude Query (Priority: P1)

As a user, I want to ask Ara to "ask Claude" a question so that I can get responses from Claude's advanced AI capabilities through my voice assistant.

**Why this priority**: This is the core feature - without the ability to send queries to Claude and receive responses, the entire feature has no value.

**Independent Test**: Can be fully tested by saying "ask Claude what is the capital of France" and receiving a spoken response from Ara containing Claude's answer.

**Acceptance Scenarios**:

1. **Given** Ara is listening and authentication is configured, **When** user says "ask Claude what is the capital of France", **Then** Ara verifies connectivity, plays an audio indicator while waiting, sends the query to Claude, and speaks the response aloud.
2. **Given** Ara is listening and authentication is configured, **When** user says "hey Ara, ask Claude to explain quantum computing", **Then** Ara sends the query to Claude and speaks a summarized response aloud.
3. **Given** Ara is listening, **When** user says "ask Claude" followed by a complex multi-sentence question, **Then** Ara captures the full question and sends it to Claude.
4. **Given** Ara is listening, **When** user triggers a Claude query, **Then** Ara first checks internet connectivity before proceeding.
5. **Given** no internet connectivity, **When** user asks a Claude question, **Then** Ara immediately informs the user that internet is unavailable without attempting the query.

---

### User Story 5 - Waiting Feedback (Priority: P2)

As a user, I want to hear an audio indicator while Ara is waiting for Claude's response so that I know my query is being processed and the system hasn't frozen.

**Why this priority**: Audio feedback is essential for voice-only interfaces where there's no visual confirmation the system is working.

**Independent Test**: Can be tested by asking Claude a question and verifying an audio indicator plays until the response begins.

**Acceptance Scenarios**:

1. **Given** user has asked Claude a question, **When** Ara is waiting for Claude's response, **Then** an audio indicator plays continuously until the response arrives.
2. **Given** audio indicator is playing, **When** Claude's response begins, **Then** the indicator stops and the response is spoken.
3. **Given** audio indicator is playing, **When** an error occurs, **Then** the indicator stops and the error message is spoken.

---

### User Story 2 - Follow-up Questions (Priority: P2)

As a user, I want a 5-second window after Claude answers to ask follow-up questions without repeating the trigger phrase, so that I can have a natural conversation flow.

**Why this priority**: Follow-up capability significantly improves the user experience for multi-turn conversations, but the feature is still useful without it.

**Independent Test**: Can be tested by asking an initial Claude question, then within 5 seconds asking a follow-up without saying "ask Claude" again.

**Acceptance Scenarios**:

1. **Given** Claude just responded to a query, **When** user speaks within 5 seconds, **Then** Ara treats the utterance as a follow-up to Claude and sends it as a continuation.
2. **Given** Claude responded to a query, **When** more than 5 seconds pass without user speech, **Then** the follow-up window closes and user must use the trigger phrase again.
3. **Given** user is in a follow-up conversation with Claude, **When** user asks another follow-up within 5 seconds of each response, **Then** the conversation continues naturally.

---

### User Story 3 - One-Time Authentication Setup (Priority: P3)

As a user, I want to authenticate Ara with my Claude Max subscription once so that I can use the Claude query feature without re-authenticating each time.

**Why this priority**: Authentication is required for the feature to work, but it's a one-time setup task rather than a daily workflow.

**Independent Test**: Can be tested by going through the authentication flow once and verifying subsequent queries work without re-authentication.

**Acceptance Scenarios**:

1. **Given** user has not authenticated, **When** user attempts to ask Claude a question, **Then** Ara prompts user to complete authentication setup.
2. **Given** user completes authentication, **When** user asks Claude a question, **Then** the query succeeds using stored credentials.
3. **Given** authentication credentials are stored, **When** Ara restarts, **Then** credentials persist and queries continue to work.

---

### User Story 6 - Query History Summarization (Priority: P3)

As a user, I want to ask Ara to summarize my Claude conversations over a time period so that I can recall key learnings and insights without re-reading individual exchanges.

**Why this priority**: History summarization adds significant value for knowledge retention but requires core query functionality to be working first.

**Independent Test**: Can be tested by asking several Claude questions, then saying "summarize my Claude conversations today" and receiving a spoken summary.

**Acceptance Scenarios**:

1. **Given** user has asked Claude questions today, **When** user says "summarize my conversation with Claude today", **Then** Ara retrieves all Claude queries/responses from today and speaks a summary.
2. **Given** user has asked Claude questions this week, **When** user says "what are the key learnings from Claude this week", **Then** Ara retrieves and summarizes Claude interactions from the past 7 days.
3. **Given** user has asked Claude questions this month, **When** user says "summarize my Claude queries this month", **Then** Ara retrieves and summarizes Claude interactions from the current month.
4. **Given** no Claude queries exist for the requested period, **When** user asks for a summary, **Then** Ara responds that no Claude conversations were found for that time period.

---

### User Story 4 - Error Handling and Feedback (Priority: P4)

As a user, I want clear spoken feedback when Claude is unavailable or an error occurs so that I understand what happened and can take action.

**Why this priority**: Good error handling improves user experience but is not required for the happy path.

**Independent Test**: Can be tested by simulating network failure and verifying Ara speaks an appropriate error message.

**Acceptance Scenarios**:

1. **Given** Claude service is unavailable, **When** user asks a Claude question, **Then** Ara speaks a friendly error message explaining the service is unavailable.
2. **Given** authentication has expired, **When** user asks a Claude question, **Then** Ara prompts user to re-authenticate.
3. **Given** 30 seconds pass without a response, **When** waiting for Claude response, **Then** Ara asks "Claude is taking longer than expected, would you like to try again?"

---

### Edge Cases

- What happens when the user's Claude Max subscription expires or is cancelled?
- How does the system handle very long Claude responses that would be tedious to listen to?
- What happens if the user interrupts Ara while it's speaking Claude's response?
- How does the system handle ambiguous trigger phrases like "ask cloud" (mishearing)?
- What happens if network connectivity is lost mid-response?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST recognize the trigger phrase "ask Claude" (and variations like "ask Claud") followed by a query
- **FR-002**: System MUST send recognized queries to the Claude service and receive responses
- **FR-003**: System MUST speak Claude's response aloud to the user using text-to-speech
- **FR-004**: System MUST provide a 5-second post-response window for follow-up questions
- **FR-005**: System MUST maintain conversation context with Claude until user explicitly ends it (e.g., "new conversation", "start over")
- **FR-005a**: System MUST recognize explicit session reset commands to clear conversation history and start fresh
- **FR-006**: System MUST securely store authentication credentials for Claude Max subscription
- **FR-007**: System MUST provide clear spoken error messages when Claude is unavailable or errors occur
- **FR-008**: System MUST instruct Claude to provide concise responses that fit within 60 seconds when spoken aloud
- **FR-009**: System MUST allow user to interrupt long responses
- **FR-010**: System MUST distinguish between Claude queries and regular Ara commands
- **FR-011**: System MUST verify internet connectivity before initiating each new Claude query
- **FR-012**: System MUST play a short repeating musical loop while waiting for Claude's response to provide user feedback
- **FR-013**: System MUST timeout after 30 seconds of waiting and offer the user the option to retry the query
- **FR-014**: System MUST log all Claude queries and responses to local MongoDB for history and audit purposes
- **FR-015**: System MUST tag all logged Claude queries with a distinct type identifier (e.g., "claude_query") to enable filtering
- **FR-016**: System MUST support time-based retrieval of Claude queries (today, this week, this month)
- **FR-017**: System MUST summarize retrieved Claude queries/responses when user requests conversation history

### Key Entities

- **Claude Session**: Represents an active conversation with Claude, including conversation history for follow-ups; persists until user explicitly resets with command like "new conversation"
- **Authentication Credentials**: Securely stored credentials for Claude Max subscription, including expiration/refresh information
- **Query**: A single user question sent to Claude; includes original utterance, type identifier ("claude_query"), session reference, follow-up flag, and timestamp; persisted to MongoDB
- **Response**: Claude's answer to a query; includes full text, type identifier ("claude_response"), query reference, and timestamp; persisted to MongoDB

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully send a query to Claude and hear a response within 10 seconds of finishing their question (for typical queries)
- **SC-002**: 95% of "ask Claude" trigger phrases are correctly recognized and routed
- **SC-003**: Follow-up questions within the 5-second window successfully continue the conversation 90% of the time
- **SC-004**: Authentication setup can be completed in under 3 minutes
- **SC-005**: Users receive clear, actionable error messages for 100% of failure scenarios
- **SC-006**: Long responses are handled such that users can understand the key information without listening for more than 60 seconds
- **SC-007**: Audio waiting indicator plays within 500ms of query submission and stops within 500ms of response arrival
- **SC-008**: Internet connectivity check completes within 2 seconds before each query
- **SC-009**: Query history summarization requests return results within 15 seconds for up to 100 queries

## Assumptions

- User has an active Claude Max subscription with valid credentials
- Local MongoDB instance is running and accessible (existing Ara infrastructure)
- Claude's response times are generally under 5 seconds for typical queries
- Text-to-speech can handle Claude's response content (no special formatting issues)
- The existing 5-second follow-up window behavior from other Ara features is the correct duration for this feature as well
- Users will primarily use this for knowledge queries rather than code generation or other output that doesn't translate well to speech
