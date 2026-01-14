# Tasks: MongoDB Data Store for Voice Agent

**Input**: Design documents from `/specs/004-mongodb-data-store/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included per Constitution Principle V (Test-Driven Development).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## User Story Mapping

| Story | Title | Priority | Key Components |
|-------|-------|----------|----------------|
| US1 | Query Time Between Events | P1 (MVP) | TimeQueryHandler, duration calculation |
| US2 | Search Activities Around Time | P2 | EventRepository.get_around_time, range queries |
| US3 | Persistent Data Storage | P3 | MongoDB client, repositories, Docker |
| US4 | Natural Language Event Logging | P4 | EventExtractor, EventPairer, semantic similarity |

**Note**: Although US3 (Persistent Storage) is P3 priority, it is a **foundational dependency** for US1 and US2. The implementation order is: Setup → Foundational (includes US3 core) → US1 → US2 → US4.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, Docker configuration, and dependency setup

- [ ] T001 Create docker/ directory at repository root
- [ ] T002 Create docker/docker-compose.yml with MongoDB 4.4.18 ARM64 configuration per research.md
- [ ] T003 [P] Add pymongo>=4.6.0 to pyproject.toml dependencies
- [ ] T004 [P] Create src/ara/storage/ module directory with __init__.py
- [ ] T005 [P] Create src/ara/commands/ directory if not exists
- [ ] T006 Create tests/unit/test_storage_client.py placeholder
- [ ] T007 [P] Create tests/integration/test_mongodb_integration.py placeholder
- [ ] T008 [P] Create tests/benchmark/test_query_latency.py placeholder

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core MongoDB infrastructure that MUST be complete before ANY user story query features

**Note**: This includes US3 core components since persistent storage is required for all queries.

### MongoDB Client & Connection

- [ ] T009 Implement StorageClient interface in src/ara/storage/client.py with:
  - MongoClient initialization with connection pooling (maxPoolSize=50, minPoolSize=10)
  - connect(), disconnect(), is_connected(), health_check() methods
  - Exponential backoff retry decorator (max 5 retries per research.md)
  - Fallback behavior when MongoDB unavailable (FR-006)

- [ ] T010 [P] Create DTOs and enums in src/ara/storage/models.py:
  - EventType enum (activity_start, activity_end, note, reminder, query)
  - ActivityStatus enum (in_progress, completed, abandoned)
  - TimeQueryType enum (duration, range_search, point_search)
  - InteractionDTO, EventDTO, ActivityDTO, TimeQueryResultDTO dataclasses

### Repository Implementations

- [ ] T011 Implement InteractionRepository in src/ara/storage/client.py:
  - save(), get_by_id(), get_by_date_range(), get_recent(), search_transcript()
  - Create indexes: timestamp, session_id, device_id, input.transcript (text)

- [ ] T012 [P] Implement EventRepository in src/ara/storage/events.py:
  - save(), get_by_id(), get_by_type()
  - Create indexes: timestamp, type+timestamp, context+timestamp, linked_event_id, activity_id

- [ ] T013 [P] Implement ActivityRepository in src/ara/storage/events.py:
  - save(), get_by_id(), get_in_progress(), complete(), get_by_name()
  - Create indexes: status+start_time, name+start_time, end_time

### Integration with Existing Logger

- [ ] T014 Modify src/ara/logger/storage.py to add MongoDBStorage backend option:
  - Keep SQLiteStorage as fallback
  - Add storage_type configuration (sqlite|mongodb)
  - Implement adapter to map existing Interaction model to InteractionDTO

- [ ] T015 Add TIME_QUERY and EVENT_LOG intent types to src/ara/router/intent.py:
  - Add patterns for "how long", "how much time", "duration between"
  - Add patterns for "what was I doing around", "what happened between"
  - Add patterns for activity logging ("I'm going to", "I'm done with", "just finished")

### Foundational Tests

- [ ] T016 Write unit tests for StorageClient in tests/unit/test_storage_client.py:
  - Test connection with mock MongoDB
  - Test retry logic with simulated failures
  - Test fallback behavior when unavailable

- [ ] T017 [P] Write integration test for MongoDB connection in tests/integration/test_mongodb_integration.py:
  - Test Docker container startup
  - Test basic CRUD operations
  - Test index creation

**Checkpoint**: MongoDB infrastructure ready - user story query features can now be implemented

---

## Phase 3: User Story 1 - Query Time Between Events (Priority: P1) 🎯 MVP

**Goal**: Users can ask "How long was I in the shower?" and get accurate duration

**Independent Test**: Ask time-based questions about logged events and verify accurate duration calculations

### Tests for User Story 1

- [ ] T018 [P] [US1] Write unit test for duration calculation in tests/unit/test_time_queries.py:
  - Test format_duration() returns human-friendly strings ("about 2 hours and 15 minutes")
  - Test duration between two events with known timestamps
  - Test handling of events not found

- [ ] T019 [P] [US1] Write integration test for duration query in tests/integration/test_time_query_flow.py:
  - Test "How long was I in the shower?" with pre-seeded events
  - Test response within 2 seconds (SC-001)

### Implementation for User Story 1

- [ ] T020 [US1] Implement TimeQueryHandler.query_duration() in src/ara/storage/queries.py:
  - Find matching start/end events by description
  - Calculate duration in milliseconds
  - Return TimeQueryResultDTO with success status

- [ ] T021 [US1] Implement TimeQueryHandler.format_duration() in src/ara/storage/queries.py:
  - Convert milliseconds to human-friendly format (FR-009)
  - Handle edge cases: <1 minute, >24 hours, exact hours

- [ ] T022 [US1] Create time_query command handler in src/ara/commands/time_query.py:
  - Handle TIME_QUERY intent from orchestrator
  - Parse duration query parameters (event descriptions)
  - Return formatted response

- [ ] T023 [US1] Modify src/ara/router/orchestrator.py to route TIME_QUERY intents:
  - Import and instantiate TimeQueryHandler
  - Route to time_query command handler
  - Handle query failures gracefully

- [ ] T024 [US1] Add benchmark test for duration query latency in tests/benchmark/test_query_latency.py:
  - Verify <2s response time (SC-001)
  - Test with varying data sizes (10, 100, 1000 events)

**Checkpoint**: User Story 1 complete - "How long was I in the shower?" works

---

## Phase 4: User Story 2 - Search Activities Around Time Point (Priority: P2)

**Goal**: Users can ask "What was I doing around 10 AM?" and get relevant activities

**Independent Test**: Query for activities around a specified time and verify relevant results returned

### Tests for User Story 2

- [ ] T025 [P] [US2] Write unit test for around-time queries in tests/unit/test_time_queries.py:
  - Test get_around_time() with 15-minute window
  - Test range_search between two times
  - Test no results case

- [ ] T026 [P] [US2] Write integration test for point search in tests/integration/test_time_query_flow.py:
  - Test "What was I doing around 10 AM?" with pre-seeded events
  - Test "What happened between 9 and noon?"
  - Test response within 2 seconds (SC-002)

### Implementation for User Story 2

- [ ] T027 [US2] Implement EventRepository.get_around_time() in src/ara/storage/events.py:
  - Query events within time_point ± window_minutes
  - Use compound index for efficient query
  - Sort by timestamp ascending

- [ ] T028 [US2] Implement EventRepository.get_in_range() in src/ara/storage/events.py:
  - Query events between start and end datetime
  - Support multi-day ranges (FR-007)

- [ ] T029 [US2] Implement TimeQueryHandler.query_around_time() in src/ara/storage/queries.py:
  - Parse time point from natural language ("10 AM", "around noon")
  - Call EventRepository.get_around_time()
  - Format results as human-readable list

- [ ] T030 [US2] Implement TimeQueryHandler.query_range() in src/ara/storage/queries.py:
  - Parse start and end times from natural language
  - Call EventRepository.get_in_range()
  - Format results with timestamps

- [ ] T031 [US2] Extend time_query command handler in src/ara/commands/time_query.py:
  - Handle point_search and range_search query types
  - Route to appropriate TimeQueryHandler method

- [ ] T032 [US2] Add benchmark test for range query latency in tests/benchmark/test_query_latency.py:
  - Verify <2s response time (SC-002)
  - Test with 30+ days of data (SC-005)

**Checkpoint**: User Story 2 complete - "What was I doing around 10 AM?" works

---

## Phase 5: User Story 3 - Persistent Data Storage (Priority: P3)

**Goal**: All interactions survive system restarts and are queryable across days/weeks

**Note**: Core persistence (MongoDB client, repositories) was implemented in Foundational phase. This phase adds data survival verification and historical queries.

**Independent Test**: Log interactions, restart system, verify data accessible

### Tests for User Story 3

- [ ] T033 [P] [US3] Write integration test for data persistence in tests/integration/test_mongodb_integration.py:
  - Save interactions, simulate disconnect/reconnect
  - Verify 100% data retained (SC-003)

- [ ] T034 [P] [US3] Write integration test for historical queries in tests/integration/test_mongodb_integration.py:
  - Seed 30+ days of data
  - Query "What did I do yesterday?"
  - Query "When was the last time I mentioned [topic]?"

### Implementation for User Story 3

- [ ] T035 [US3] Implement "What did I do yesterday?" query in src/ara/storage/queries.py:
  - Calculate yesterday's date range
  - Query interactions and summarize activities

- [ ] T036 [US3] Implement "When was the last time I mentioned [topic]?" in src/ara/storage/queries.py:
  - Use text search on transcript index
  - Return most recent match with timestamp

- [ ] T037 [US3] Implement HISTORY_QUERY intent handler in src/ara/router/orchestrator.py:
  - Route history questions to storage queries
  - Handle "yesterday", "last week", "last time I mentioned"

- [ ] T038 [US3] Add data archiving foundation in src/ara/storage/client.py:
  - Create archive collection schema
  - Implement archive_old_data() method (FR-010)
  - Add user notification for archive queries (FR-011)

**Checkpoint**: User Story 3 complete - data persists across restarts, historical queries work

---

## Phase 6: User Story 4 - Natural Language Event Logging (Priority: P4)

**Goal**: System automatically extracts events from natural speech ("I'm heading to the gym")

**Independent Test**: Speak naturally and verify events extracted and stored

### Tests for User Story 4

- [ ] T039 [P] [US4] Write unit test for event extraction in tests/unit/test_event_extraction.py:
  - Test "I'm going to the gym" → activity_start event
  - Test "Just finished my workout" → activity_end event
  - Test "Remember to call the dentist" → reminder event

- [ ] T040 [P] [US4] Write unit test for event pairing in tests/unit/test_event_extraction.py:
  - Test "gym" ↔ "workout" semantic similarity >0.7
  - Test temporal proximity scoring
  - Test wrong temporal order rejection

- [ ] T041 [P] [US4] Write integration test for event flow in tests/integration/test_event_extraction_flow.py:
  - Say "I'm going to the gym" → event stored
  - Say "Done with my workout" → paired with gym event
  - Query "How long was I at the gym?" → correct duration

### Implementation for User Story 4

- [ ] T042 [US4] Create synonym dictionary in src/ara/storage/synonyms.json:
  - gym: workout, training, exercise, fitness
  - shower: bath, washing up
  - cooking: making food, preparing meal

- [ ] T043 [US4] Implement EventExtractor.extract() in src/ara/storage/events.py:
  - Pattern matching for activity start/end phrases
  - Extract context from natural language
  - Return list of EventDTO

- [ ] T044 [US4] Implement EventPairer.calculate_similarity() in src/ara/storage/events.py:
  - Simple word overlap + synonym matching (lightweight for Pi)
  - Return similarity score 0-1

- [ ] T045 [US4] Implement EventPairer.find_matching_start() in src/ara/storage/events.py:
  - Query unlinked start events within 4-hour window
  - Score each candidate with semantic + temporal + entity factors
  - Return best match if score >0.7

- [ ] T046 [US4] Implement EventRepository.find_unlinked_start_events() in src/ara/storage/events.py:
  - Query activity_start events without linked_event_id
  - Filter by max_age_hours
  - Return candidates for pairing

- [ ] T047 [US4] Implement Activity creation and completion in src/ara/storage/events.py:
  - Create Activity when start event extracted
  - Complete Activity when end event paired
  - Calculate and store duration_ms

- [ ] T048 [US4] Integrate event extraction into orchestrator in src/ara/router/orchestrator.py:
  - Call EventExtractor.extract() on every interaction
  - Attempt event pairing for activity_end events
  - Store extracted events linked to interaction

**Checkpoint**: User Story 4 complete - natural language events extracted and paired

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T049 [P] Update ara-voice-assistant-pi4-setup.md with MongoDB Docker setup instructions
- [ ] T050 [P] Add voice command reference for time queries to documentation
- [ ] T051 Run full test suite and fix any regressions
- [ ] T052 [P] Performance optimization: verify all queries <2s on Pi 4 hardware
- [ ] T053 Validate quickstart.md scenarios end-to-end
- [ ] T054 Code cleanup: remove unused imports, fix linting warnings
- [ ] T055 Add error messages for common failure cases (MongoDB down, events not found)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ──────────────────────────────────────┐
                                                       │
Phase 2 (Foundational) ◄──────────────────────────────┘
    │
    ├── T009-T017 complete BEFORE user stories
    │
    ▼
┌───────────────────┬───────────────────┬───────────────────┐
│                   │                   │                   │
▼                   ▼                   ▼                   │
Phase 3 (US1)       Phase 4 (US2)       Phase 5 (US3)       │
P1 - MVP            P2                  P3                  │
Duration queries    Around-time search  Persistence         │
                                                            │
└───────────────────┴───────────────────┴───────────────────┘
                                        │
                                        ▼
                                Phase 6 (US4)
                                P4 - Event extraction
                                (Depends on US1-US3)
                                        │
                                        ▼
                                Phase 7 (Polish)
```

### User Story Dependencies

| Story | Can Start After | Depends On |
|-------|-----------------|------------|
| US1 | Foundational (Phase 2) | StorageClient, EventRepository |
| US2 | Foundational (Phase 2) | StorageClient, EventRepository |
| US3 | Foundational (Phase 2) | Core already in Foundational |
| US4 | US1 + US2 + US3 | All query/storage infrastructure |

### Parallel Opportunities

**Within Phase 1 (Setup)**:
```
T003, T004, T005 can run in parallel (different files)
T006, T007, T008 can run in parallel (test placeholders)
```

**Within Phase 2 (Foundational)**:
```
T011, T012, T013 can run in parallel after T009, T010 (different repository files)
T016, T017 can run in parallel (test files)
```

**Within User Story Phases**:
```
US1: T018, T019 tests in parallel
US2: T025, T026 tests in parallel
US3: T033, T034 tests in parallel
US4: T039, T040, T041 tests in parallel
```

**Cross-Story (with multiple developers)**:
```
After Foundational complete:
  - Dev A: US1 (T018-T024)
  - Dev B: US2 (T025-T032)
  - Dev C: US3 (T033-T038)
Then:
  - All: US4 (T039-T048) - requires US1-US3 infrastructure
```

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write unit test for duration calculation in tests/unit/test_time_queries.py"
Task: "Write integration test for duration query in tests/integration/test_time_query_flow.py"

# After tests pass, implementation sequentially:
Task: "Implement TimeQueryHandler.query_duration() in src/ara/storage/queries.py"
Task: "Implement TimeQueryHandler.format_duration() in src/ara/storage/queries.py"
Task: "Create time_query command handler in src/ara/commands/time_query.py"
Task: "Modify src/ara/router/orchestrator.py to route TIME_QUERY intents"
Task: "Add benchmark test for duration query latency"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T017) - CRITICAL
3. Complete Phase 3: User Story 1 (T018-T024)
4. **STOP and VALIDATE**: "How long was I in the shower?" works
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → MongoDB running, basic storage works
2. Add User Story 1 → Duration queries work → **MVP!**
3. Add User Story 2 → Around-time searches work
4. Add User Story 3 → Historical queries work
5. Add User Story 4 → Natural language event extraction works
6. Polish phase → Production ready

### Suggested Order for Single Developer

```
Week 1: T001-T017 (Setup + Foundational)
Week 2: T018-T024 (US1 - MVP)
Week 3: T025-T032 (US2)
Week 4: T033-T048 (US3 + US4)
Week 5: T049-T055 (Polish)
```

---

## Task Summary

| Phase | Task Range | Count | Focus |
|-------|-----------|-------|-------|
| Setup | T001-T008 | 8 | Docker, dependencies, structure |
| Foundational | T009-T017 | 9 | MongoDB client, repositories, intents |
| US1 (P1 MVP) | T018-T024 | 7 | Duration queries |
| US2 (P2) | T025-T032 | 8 | Around-time search |
| US3 (P3) | T033-T038 | 6 | Persistence, historical queries |
| US4 (P4) | T039-T048 | 10 | Event extraction, pairing |
| Polish | T049-T055 | 7 | Documentation, optimization |
| **Total** | | **55** | |

### MVP Scope (Recommended)

**Minimum Viable Product**: Tasks T001-T024 (24 tasks)
- Setup + Foundational + User Story 1
- Delivers: "How long was I in the shower?" capability
- Can demo and validate before continuing

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Write tests FIRST, ensure they FAIL before implementation (TDD per Constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Docker must be running for integration tests
