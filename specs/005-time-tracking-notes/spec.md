# Feature Specification: Enhanced Note-Taking & Time Tracking

**Feature Branch**: `005-time-tracking-notes`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Enhanced Note-Taking & Time Tracking - Optimize Ara for capturing rich contextual notes and tracking time spent on activities. Features: 1) Rich event extraction (extract people, topics, locations, context from natural speech), 2) Auto-categorization (work, personal, health, errands), 3) Activity duration tracking ("starting X" / "done with X"), 4) Daily digest ("How did I spend my time today?" with breakdown by category), 5) Weekly insights (patterns, time allocation analysis). Goal: Help user interrogate their day and understand how time is best spent."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quick Voice Notes with Context (Priority: P1)

As a user, I want to capture notes via voice with automatic extraction of people, topics, and locations so that I have rich, searchable records without manual tagging.

**Why this priority**: This is the core value proposition - capturing information naturally while the system does the heavy lifting of organization. Without this, the user gains no efficiency over manual note-taking.

**Independent Test**: Can be fully tested by speaking notes like "Just had a meeting with Sarah about the Q1 budget at the downtown office" and verifying that people (Sarah), topics (Q1 budget), and locations (downtown office) are extracted and stored.

**Acceptance Scenarios**:

1. **Given** the voice assistant is active, **When** user says "I just talked to John about the project deadline", **Then** the system extracts person="John", topic="project deadline" and stores the note with these attributes
2. **Given** the voice assistant is active, **When** user says "Meeting at Starbucks with the marketing team about campaign launch", **Then** the system extracts location="Starbucks", people="marketing team", topic="campaign launch"
3. **Given** a note was captured with extracted entities, **When** user asks "What did I discuss with John?", **Then** the system returns all notes involving the person "John"

---

### User Story 2 - Activity Duration Tracking (Priority: P1)

As a user, I want to track how long I spend on activities by saying "starting X" and "done with X" so that I can understand my time allocation.

**Why this priority**: Time tracking is fundamental to the goal of understanding "how time is best spent." This enables all downstream analysis features.

**Independent Test**: Can be tested by saying "starting workout", waiting, then "done with workout" and verifying the duration is calculated and stored.

**Acceptance Scenarios**:

1. **Given** no activity is in progress, **When** user says "starting my workout", **Then** the system records activity="workout" with start time and confirms "Started tracking workout"
2. **Given** an activity "workout" is in progress, **When** user says "done with my workout", **Then** the system calculates duration, stores it, and confirms "Workout completed - 45 minutes"
3. **Given** an activity "reading" is in progress, **When** user starts a different activity "cooking", **Then** the system auto-ends "reading" and starts "cooking" (single active activity at a time)
4. **Given** user says "finished coding" but no "coding" activity was started, **When** the system processes this, **Then** it creates a completed activity with estimated duration based on context or asks for clarification

---

### User Story 3 - Daily Time Digest (Priority: P2)

As a user, I want to ask "How did I spend my time today?" and receive a breakdown by category so that I can reflect on my day's productivity.

**Why this priority**: This is the primary interrogation feature that delivers immediate value from tracked data. Depends on P1 stories for data.

**Independent Test**: Can be tested by tracking several activities throughout the day, then asking for a digest and verifying the breakdown is accurate and categorized.

**Acceptance Scenarios**:

1. **Given** user has tracked 3 activities today (2 hours work, 1 hour exercise, 30 minutes errands), **When** user asks "How did I spend my time today?", **Then** system responds with categorized breakdown: "Today you spent 2 hours on work, 1 hour on health, and 30 minutes on errands"
2. **Given** user has no tracked activities today, **When** user asks "How did I spend my time today?", **Then** system responds "I don't have any activities tracked for today yet"
3. **Given** user asks "What did I do this morning?", **When** the system processes this, **Then** it filters activities by time range (before noon) and provides summary

---

### User Story 4 - Auto-Categorization (Priority: P2)

As a user, I want my notes and activities to be automatically categorized (work, personal, health, errands) so that I can analyze time by category without manual tagging.

**Why this priority**: Enables meaningful analysis without user friction. Required for useful daily/weekly digests.

**Independent Test**: Can be tested by capturing various notes/activities and verifying they are assigned appropriate categories.

**Acceptance Scenarios**:

1. **Given** user says "starting workout", **When** the system processes this, **Then** it auto-categorizes as "health"
2. **Given** user says "meeting with the engineering team about sprint planning", **When** the system processes this, **Then** it auto-categorizes as "work"
3. **Given** user says "picking up groceries", **When** the system processes this, **Then** it auto-categorizes as "errands"
4. **Given** the system cannot determine category with confidence, **When** processing the note, **Then** it assigns "uncategorized" and optionally asks user to clarify

---

### User Story 5 - Weekly Insights (Priority: P3)

As a user, I want to ask for weekly insights to understand patterns in how I spend my time so that I can make informed decisions about time management.

**Why this priority**: Advanced analytics that provide strategic value. Requires sufficient data from P1/P2 stories.

**Independent Test**: Can be tested by accumulating a week of data and requesting insights, verifying patterns are identified and communicated.

**Acceptance Scenarios**:

1. **Given** user has a week of tracked activities, **When** user asks "How did I spend my time this week?", **Then** system provides weekly breakdown by category with totals and percentages
2. **Given** user has two weeks of data, **When** user asks "What patterns do you see in my time?", **Then** system identifies trends (e.g., "You spend most of your productive hours in the morning", "Wednesdays are your busiest work days")
3. **Given** user asks "Am I spending enough time on health?", **When** the system processes this, **Then** it calculates health category percentage and compares to user-defined goals or general recommendations

---

### Edge Cases

- What happens when user ends an activity that was never started?
  - System creates a completed activity and estimates duration or asks for clarification
- What happens when user starts an activity but never ends it?
  - System auto-closes activities after configurable timeout (default: 4 hours) or at end of day
- What happens when extracted entities are ambiguous (e.g., "John" could be multiple people)?
  - System stores as-is; future disambiguation can use context or ask user
- What happens when user asks for digest with no data?
  - System responds helpfully that no data is available for the requested period
- What happens when voice recognition misses context?
  - System stores what it captures; user can query and correct via "Actually, that meeting was with Sarah, not Sandra"

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract people, topics, and locations from natural speech using contextual analysis
- **FR-002**: System MUST store notes with extracted entities as searchable attributes
- **FR-003**: System MUST support starting activities via phrases like "starting X", "beginning X", "I'm going to X"
- **FR-004**: System MUST support ending activities via phrases like "done with X", "finished X", "completed X"
- **FR-005**: System MUST calculate and store duration when an activity is ended
- **FR-006**: System MUST auto-categorize notes and activities into predefined categories (work, personal, health, errands, uncategorized)
- **FR-007**: System MUST provide daily digest with time breakdown by category when requested
- **FR-008**: System MUST provide weekly summary with totals and percentages by category
- **FR-009**: System MUST identify basic patterns in time usage over multiple weeks
- **FR-010**: System MUST support querying notes by extracted entities (people, topics, locations)
- **FR-011**: System MUST handle overlapping activities by auto-closing previous activity when new one starts
- **FR-012**: System MUST auto-close activities after configurable timeout to prevent orphaned activities

### Key Entities

- **Note**: A captured voice entry with timestamp, raw transcript, extracted entities (people, topics, locations), category, and optional activity association
- **Activity**: A tracked time block with name, start time, end time (nullable), duration, category, and associated notes
- **Category**: Classification for notes and activities (work, personal, health, errands, uncategorized)
- **Person**: Extracted reference to a person mentioned in notes (name, optional disambiguation hints)
- **Topic**: Extracted subject matter from notes (keywords, phrases)
- **Location**: Extracted place reference from notes (name, optional coordinates)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can capture a note with automatic entity extraction in under 5 seconds of speaking
- **SC-002**: Entity extraction (people, topics, locations) achieves 80% accuracy on typical conversational inputs
- **SC-003**: Auto-categorization achieves 85% accuracy for clear-cut categories (workout=health, meeting=work)
- **SC-004**: Daily digest is generated and spoken in under 3 seconds
- **SC-005**: Users can query "What did I discuss with [person]?" and receive relevant results within 2 seconds
- **SC-006**: Activity duration tracking is accurate to within 1 minute
- **SC-007**: 90% of users can successfully track an activity (start to finish) on first attempt without instructions

## Assumptions

- User has a single active activity at any time (no parallel activity tracking)
- Categories are fixed (work, personal, health, errands, uncategorized) - custom categories not in scope
- Entity extraction uses local LLM capabilities without requiring cloud services
- Historical data is stored in MongoDB as per existing infrastructure
- Week is defined as Monday-Sunday for weekly insights
- Timeout for auto-closing activities defaults to 4 hours
