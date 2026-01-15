# Tasks: Enhanced Note-Taking & Time Tracking

**Input**: Design documents from `/specs/005-time-tracking-notes/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Tests**: Included per constitution TDD requirement ("Will write tests first for extraction, tracking")

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- Includes exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure and shared dependencies

- [ ] T001 Create notes module directory structure at src/ara/notes/
- [ ] T002 [P] Create activities module directory structure at src/ara/activities/
- [ ] T003 [P] Create digest module directory structure at src/ara/digest/
- [ ] T004 [P] Create test directories at tests/unit/ and tests/integration/ if not exist

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models and infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create shared Category enum in src/ara/notes/models.py (WORK, PERSONAL, HEALTH, ERRANDS, UNCATEGORIZED)
- [ ] T006 Create categorizer module with keyword-based classification in src/ara/notes/categorizer.py
- [ ] T007 [P] Add new intents to src/ara/router/intent.py (NOTE_CAPTURE, ACTIVITY_START, ACTIVITY_STOP, DIGEST_DAILY, DIGEST_WEEKLY, NOTE_QUERY)
- [ ] T008 [P] Create NoteDTO and ActivityDTO in src/ara/storage/models.py for MongoDB serialization
- [ ] T009 Unit tests for categorizer in tests/unit/test_categorizer.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Quick Voice Notes with Context (Priority: P1) 🎯 MVP

**Goal**: Capture notes via voice with automatic extraction of people, topics, and locations

**Independent Test**: Say "Just had a meeting with Sarah about the Q1 budget at the downtown office" and verify entities extracted

### Tests for User Story 1

- [ ] T010 [P] [US1] Unit tests for entity extractor in tests/unit/test_extractor.py
- [ ] T011 [P] [US1] Integration test for note capture flow in tests/integration/test_note_flow.py

### Implementation for User Story 1

- [ ] T012 [US1] Create Note dataclass in src/ara/notes/models.py (transcript, people, topics, locations, category, timestamp)
- [ ] T013 [US1] Implement EntityExtractor using Ollama JSON prompting in src/ara/notes/extractor.py
- [ ] T014 [US1] Implement NoteService with capture() and find_by_person() in src/ara/notes/service.py
- [ ] T015 [US1] Export public API in src/ara/notes/__init__.py
- [ ] T016 [US1] Add NOTE_CAPTURE and NOTE_QUERY intent handlers in src/ara/router/orchestrator.py

**Checkpoint**: Can capture notes with entity extraction and query by person

---

## Phase 4: User Story 2 - Activity Duration Tracking (Priority: P1)

**Goal**: Track activity durations via "starting X" and "done with X" voice commands

**Independent Test**: Say "starting workout", wait, say "done with workout" and verify duration calculated

### Tests for User Story 2

- [ ] T017 [P] [US2] Unit tests for activity tracker in tests/unit/test_activity_tracker.py
- [ ] T018 [P] [US2] Integration test for activity flow in tests/integration/test_activity_flow.py

### Implementation for User Story 2

- [ ] T019 [US2] Create Activity dataclass and ActivityStatus enum in src/ara/activities/models.py
- [ ] T020 [US2] Implement ActivityTracker with start(), stop(), get_active() in src/ara/activities/tracker.py
- [ ] T021 [US2] Implement timeout auto-close logic in src/ara/activities/timeout.py
- [ ] T022 [US2] Export public API in src/ara/activities/__init__.py
- [ ] T023 [US2] Add ACTIVITY_START and ACTIVITY_STOP intent handlers in src/ara/router/orchestrator.py

**Checkpoint**: Can start/stop activities and track durations

---

## Phase 5: User Story 3 - Daily Time Digest (Priority: P2)

**Goal**: Provide daily breakdown by category when user asks "How did I spend my time today?"

**Independent Test**: Track activities, then ask "How did I spend my time today?" and verify breakdown

**Dependencies**: Requires US2 (Activity Tracking) data to summarize

### Tests for User Story 3

- [ ] T024 [P] [US3] Unit tests for daily digest in tests/unit/test_daily_digest.py

### Implementation for User Story 3

- [ ] T025 [US3] Implement DailyDigest generator with MongoDB aggregation in src/ara/digest/daily.py
- [ ] T026 [US3] Export public API in src/ara/digest/__init__.py
- [ ] T027 [US3] Add DIGEST_DAILY intent handler in src/ara/router/orchestrator.py

**Checkpoint**: Can generate daily time breakdown by category

---

## Phase 6: User Story 4 - Auto-Categorization (Priority: P2)

**Goal**: Automatically categorize notes and activities (work, personal, health, errands)

**Independent Test**: Say "starting workout" → auto-categorizes as "health"; "meeting with team" → "work"

**Note**: Foundational categorizer (T006) provides basic implementation; this phase adds LLM fallback

### Implementation for User Story 4

- [ ] T028 [US4] Add LLM fallback to categorizer for ambiguous cases in src/ara/notes/categorizer.py
- [ ] T029 [US4] Update NoteService.capture() to use enhanced categorizer in src/ara/notes/service.py
- [ ] T030 [US4] Update ActivityTracker.start() to use enhanced categorizer in src/ara/activities/tracker.py

**Checkpoint**: Notes and activities auto-categorized with 85% accuracy

---

## Phase 7: User Story 5 - Weekly Insights (Priority: P3)

**Goal**: Provide weekly summary with patterns and trends

**Independent Test**: Accumulate week of data, ask "How did I spend my time this week?" and verify patterns identified

**Dependencies**: Requires US2+US3 data for pattern analysis

### Implementation for User Story 5

- [ ] T031 [US5] Implement WeeklyDigest generator in src/ara/digest/weekly.py
- [ ] T032 [US5] Implement InsightGenerator for pattern detection in src/ara/digest/insights.py
- [ ] T033 [US5] Add DIGEST_WEEKLY intent handler in src/ara/router/orchestrator.py
- [ ] T034 [US5] Update src/ara/digest/__init__.py exports

**Checkpoint**: Can generate weekly breakdown with pattern insights

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration and validation

- [ ] T035 [P] Add MongoDB indexes for notes collection (timestamp, people, topics, category)
- [ ] T036 [P] Add MongoDB indexes for activities collection (start_time, status, category)
- [ ] T037 Run quickstart.md validation scenarios
- [ ] T038 Performance benchmark: entity extraction <2s, digest <3s
- [ ] T039 Update voice command documentation

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ────────────────────────────────────────────┐
                                                            │
Phase 2 (Foundational) ─────────────────────────────────────┤
    │                                                       │
    ├──► Phase 3 (US1: Notes) ──────────────────────────────┤
    │                                                       │
    ├──► Phase 4 (US2: Activities) ─────────────────────────┤
    │         │                                             │
    │         └──► Phase 5 (US3: Daily Digest) ─────────────┤
    │                                                       │
    ├──► Phase 6 (US4: Auto-Categorization) ────────────────┤
    │                                                       │
    └──► Phase 7 (US5: Weekly Insights) ────────────────────┤
              (depends on US2+US3)                          │
                                                            │
Phase 8 (Polish) ◄──────────────────────────────────────────┘
```

### User Story Dependencies

| Story | Can Start After | Dependencies |
|-------|-----------------|--------------|
| US1 (Notes) | Phase 2 | None |
| US2 (Activities) | Phase 2 | None |
| US3 (Daily Digest) | US2 complete | Uses activity data |
| US4 (Auto-Categorization) | Phase 2 | None |
| US5 (Weekly Insights) | US2+US3 complete | Uses activity + digest |

### Parallel Opportunities

**After Phase 2 completes, these can run in parallel:**
- US1 (Notes) and US2 (Activities) - independent modules
- US4 (Auto-Categorization) - enhances both

**Sequential:**
- US3 (Daily Digest) after US2
- US5 (Weekly Insights) after US3

---

## Parallel Example: Starting Implementation

```bash
# After Phase 2 (Foundational) completes:

# Developer A - User Story 1 (Notes):
Task: "T010 [P] [US1] Unit tests for entity extractor"
Task: "T012 [US1] Create Note dataclass"
Task: "T013 [US1] Implement EntityExtractor"

# Developer B - User Story 2 (Activities):
Task: "T017 [P] [US2] Unit tests for activity tracker"
Task: "T019 [US2] Create Activity dataclass"
Task: "T020 [US2] Implement ActivityTracker"
```

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Notes) → Test independently
4. Complete Phase 4: User Story 2 (Activities) → Test independently
5. **STOP and VALIDATE**: Both P1 stories functional
6. Deploy/demo as MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 (Notes) + US2 (Activities) → MVP (can track time, capture notes)
3. US3 (Daily Digest) → Can ask "how did I spend today?"
4. US4 (Auto-Categorization) → Better category accuracy
5. US5 (Weekly Insights) → Advanced analytics

---

## Task Summary

| Phase | Story | Task Count |
|-------|-------|------------|
| Phase 1 | Setup | 4 |
| Phase 2 | Foundational | 5 |
| Phase 3 | US1 (Notes) | 7 |
| Phase 4 | US2 (Activities) | 7 |
| Phase 5 | US3 (Daily Digest) | 4 |
| Phase 6 | US4 (Auto-Categorization) | 3 |
| Phase 7 | US5 (Weekly Insights) | 4 |
| Phase 8 | Polish | 5 |
| **Total** | | **39 tasks** |

---

## Notes

- TDD approach: Write tests (T010, T011, T017, T018, T024) FIRST and ensure they FAIL before implementation
- Entity extraction uses Ollama JSON prompting per research.md
- Categorization uses keyword-first with LLM fallback per research.md
- Single active activity constraint enforced in ActivityTracker
- 4-hour timeout for auto-close per spec.md assumptions
