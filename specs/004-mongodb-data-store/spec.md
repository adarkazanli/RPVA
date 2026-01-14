# Feature Specification: MongoDB Data Store for Voice Agent

**Feature Branch**: `004-mongodb-data-store`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Deploy a local MongoDB in a Docker instance and store all the data in it. Evolve the voice agent to easily manipulate the data by analyzing the text, and do time manipulation such as how long the time was between two events or search for all activities around a specific point."

## Clarifications

### Session 2026-01-14

- Q: What happens when storage capacity limits are approached? → A: Auto-archive older data (still queryable but slower access)
- Q: How should the system link activity end events to start events? → A: Semantic similarity matching with time proximity constraints (e.g., "gym" ↔ "workout" within reasonable time window)
- Q: How should the system handle queries about very old data? → A: Query archive with user notification (e.g., "Searching older records...")

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query Time Between Events (Priority: P1)

As a user, I want to ask the voice agent how much time passed between two events so that I can understand the duration of activities or gaps between actions.

**Why this priority**: This is the core time manipulation capability that enables users to analyze their historical interactions. It provides immediate value by answering questions like "How long was I in the shower?" or "How much time passed between when I left and came back?"

**Independent Test**: Can be fully tested by asking time-based questions about logged events and verifying accurate duration calculations.

**Acceptance Scenarios**:

1. **Given** I have previously logged "I'm going to take a shower" and later "I'm done with my shower", **When** I ask "How long was I in the shower?", **Then** the system returns the accurate time difference between these two events.

2. **Given** I have multiple events logged throughout the day, **When** I ask "How long was it between my first and last call today?", **Then** the system identifies the relevant events and calculates the duration.

3. **Given** I ask about events that don't exist, **When** I say "How long between my meeting and lunch?", **Then** the system responds that it couldn't find matching events.

---

### User Story 2 - Search Activities Around a Time Point (Priority: P2)

As a user, I want to search for all activities that occurred around a specific time so that I can recall what I was doing at a particular moment.

**Why this priority**: Enables contextual recall which is highly valuable for users trying to remember sequences of events or activities around a specific time.

**Independent Test**: Can be tested by querying for activities around a specified time and verifying relevant results are returned.

**Acceptance Scenarios**:

1. **Given** I have logged multiple activities throughout the day, **When** I ask "What was I doing around 10 AM?", **Then** the system returns activities within a reasonable window of that time (e.g., 15 minutes before and after).

2. **Given** I ask about a time period with no logged activities, **When** I say "What was I doing around 3 AM?", **Then** the system responds that no activities were found during that period.

3. **Given** activities span across multiple hours, **When** I ask "What happened between 9 AM and noon?", **Then** the system returns all logged activities within that range.

---

### User Story 3 - Persistent Data Storage (Priority: P3)

As a user, I want all my voice agent interactions and data to be persistently stored so that my history survives system restarts and I can query historical data from previous days or weeks.

**Why this priority**: Foundation for all other features - without persistent storage, time queries and activity searches would be limited to current session only.

**Independent Test**: Can be tested by logging interactions, restarting the system, and verifying data is still accessible.

**Acceptance Scenarios**:

1. **Given** I have logged interactions over multiple days, **When** I restart the voice agent system, **Then** all previous interactions remain accessible and queryable.

2. **Given** I ask "What did I do yesterday?", **When** the system queries stored data, **Then** I receive a summary of yesterday's logged activities.

3. **Given** I have weeks of interaction history, **When** I ask "When was the last time I mentioned [topic]?", **Then** the system searches through historical data and returns the most recent match.

---

### User Story 4 - Natural Language Event Logging (Priority: P4)

As a user, I want the voice agent to automatically extract and store meaningful events from my natural speech so that I don't have to explicitly structure my commands.

**Why this priority**: Improves user experience by making data capture seamless and natural, building on top of the storage foundation.

**Independent Test**: Can be tested by speaking naturally and verifying that relevant events are extracted and stored.

**Acceptance Scenarios**:

1. **Given** I say "I'm heading to the gym now", **When** the system processes this, **Then** it extracts and stores an "activity started" event with context "gym" and current timestamp.

2. **Given** I say "Just finished my workout", **When** the system processes this, **Then** it stores an "activity completed" event that can be linked to the previous "heading to gym" event.

3. **Given** I mention a reminder or note, **When** I say "Remember I need to call the dentist tomorrow", **Then** the system stores this as a distinct "reminder/note" type event.

---

### Edge Cases

- What happens when the user asks about time between events that cannot be logically paired (e.g., "How long between breakfast and my meeting?" when there's no breakfast logged)?
- How does the system handle timezone changes or daylight saving time transitions?
- When storage approaches capacity limits, older data is automatically archived (remains queryable with slower access times).
- Queries about very old data (months or years ago) search the archive with user notification (e.g., "Searching older records...") to set expectations about potentially slower response times.
- What happens if the database becomes temporarily unavailable?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store all voice agent interactions with timestamps in persistent storage that survives system restarts.
- **FR-002**: System MUST support querying the time duration between two identified events.
- **FR-003**: System MUST support searching for activities within a specified time window (around a point or between two times).
- **FR-004**: System MUST extract meaningful events from natural language input (activities started/completed, notes, reminders).
- **FR-005**: System MUST run the data store as a containerized service that can be started and stopped independently.
- **FR-006**: System MUST provide fallback behavior when the data store is temporarily unavailable.
- **FR-007**: System MUST support queries spanning multiple days, weeks, or longer periods of historical data.
- **FR-008**: System MUST distinguish between different types of events (activities, reminders, queries, notes) for targeted searching.
- **FR-009**: System MUST return human-friendly time durations (e.g., "about 2 hours and 15 minutes" rather than raw timestamps).
- **FR-010**: System MUST automatically archive data older than the configured threshold when storage capacity is approached, keeping archived data queryable with acceptable degraded performance.
- **FR-011**: System MUST notify the user when searching archived/older data (e.g., "Searching older records...") to set expectations about potentially longer response times.

### Key Entities

- **Interaction**: Represents a single voice agent interaction - includes timestamp, raw transcript, intent type, response given, and any extracted events.
- **Event**: Represents a meaningful occurrence extracted from interactions - includes event type (activity_start, activity_end, note, reminder, query), timestamp, context/description, and optional linkage to related events.
- **Activity**: Represents a paired activity with start and end events - includes activity type/name, start time, end time, duration, and status (in_progress, completed). Start and end events are linked using semantic similarity matching (e.g., "gym" ↔ "workout") combined with time proximity constraints.
- **TimeQuery**: Represents a user's request for time-based information - includes query type (duration, range_search, point_search), parameters, and results.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can query time between two events and receive accurate results within 2 seconds of asking.
- **SC-002**: Users can search for activities around a specific time and receive relevant results within 2 seconds.
- **SC-003**: System retains 100% of interaction data across restarts with no data loss.
- **SC-004**: 90% of natural language time queries are correctly interpreted and answered on first attempt.
- **SC-005**: System supports querying at least 30 days of historical interaction data.
- **SC-006**: Time calculations are accurate to within 1 minute for durations and exact for timestamps.
- **SC-007**: System gracefully handles database unavailability by queuing interactions and notifying user, with automatic recovery when connection is restored.

## Assumptions

- Users will primarily query recent history (last few days to weeks) rather than very old data.
- The Docker environment is available on the deployment machine.
- Time queries will typically involve events from the same day or within a few days of each other.
- The system operates in a single timezone per deployment (no multi-timezone support required initially).
- Storage capacity will be sufficient for at least 6 months of typical usage before any cleanup is needed.
- Events will be extracted best-effort; users understand not all spoken content will be captured as queryable events.
