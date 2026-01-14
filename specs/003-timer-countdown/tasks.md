# Tasks: Timer Countdown Announcement

**Input**: Design documents from `/specs/003-timer-countdown/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/voice-commands.md

**Tests**: Tests are included per constitution requirement (Principle V: Test-Driven Development).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project structure verification and shared infrastructure

- [x] T001 Verify existing timer/reminder infrastructure from 002-personality-timers is functional
- [x] T002 [P] Add `get_user_profile_path()` function to src/ara/config/loader.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Create UserProfile dataclass with name and preferences fields in src/ara/config/user_profile.py
- [x] T004 [P] Add `load_user_profile()` function with JSON loading and defaults in src/ara/config/user_profile.py
- [x] T005 [P] Add `save_user_profile()` function for persistence in src/ara/config/user_profile.py
- [x] T006 Add user_profile module exports to src/ara/config/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Countdown Announcement (Priority: P1) 🎯 MVP

**Goal**: System begins a 5-second verbal countdown before any timer/reminder reaches zero

**Independent Test**: Set a 10-second timer and verify countdown "5..4..3..2..1..now" begins at 5 seconds remaining

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] [US1] Unit test for countdown phrase generation in tests/unit/test_countdown.py
- [x] T008 [P] [US1] Unit test for countdown timing accuracy (<200ms variance) in tests/unit/test_countdown.py
- [x] T009 [P] [US1] Unit test for short timer handling (<5s) in tests/unit/test_countdown.py
- [x] T010 [P] [US1] Unit test for overlapping countdown combination in tests/unit/test_countdown.py

### Implementation for User Story 1

- [x] T011 [US1] Add `_countdown_active: dict[UUID, bool]` tracking attribute to Orchestrator.__init__ in src/ara/router/orchestrator.py
- [x] T012 [US1] Add `_get_upcoming_reminders(seconds: int)` method to find reminders within time window in src/ara/router/orchestrator.py
- [x] T013 [US1] Add `_generate_countdown_phrase(reminders, user_name)` method for phrase construction in src/ara/router/orchestrator.py
- [x] T014 [US1] Add `_start_countdown(reminders)` method with TTS sequencing at 1-second intervals in src/ara/router/orchestrator.py
- [x] T015 [US1] Modify `_check_timers_and_reminders()` to detect 5-second threshold and initiate countdown in src/ara/router/orchestrator.py
- [x] T016 [US1] Add countdown cancellation check before each number in _start_countdown in src/ara/router/orchestrator.py
- [x] T017 [US1] Handle timers shorter than 5 seconds by starting countdown from remaining time in src/ara/router/orchestrator.py

**Checkpoint**: Countdown announcement works with generic "Hey" address

---

## Phase 4: User Story 2 - Personalized Countdown (Priority: P2)

**Goal**: Countdown addresses user by configured name (e.g., "Ammar, you should...")

**Independent Test**: Configure user name, set timer, verify countdown includes user's name

### Tests for User Story 2

- [x] T018 [P] [US2] Unit test for user profile load/save in tests/unit/test_user_profile.py
- [x] T019 [P] [US2] Unit test for name extraction in countdown phrase in tests/unit/test_countdown.py
- [x] T020 [P] [US2] Unit test for fallback to "Hey" when name not configured in tests/unit/test_countdown.py

### Implementation for User Story 2

- [x] T021 [US2] Add USER_NAME_SET intent type to IntentType enum in src/ara/router/intent.py
- [x] T022 [US2] Add intent patterns for "my name is", "call me", "set my name to" in src/ara/router/intent.py
- [x] T023 [US2] Add name entity extraction to intent classifier in src/ara/router/intent.py
- [x] T024 [US2] Load user profile in Orchestrator.__init__ and cache user name in src/ara/router/orchestrator.py
- [x] T025 [US2] Add `_handle_user_name_set(intent)` handler method in src/ara/router/orchestrator.py
- [x] T026 [US2] Wire USER_NAME_SET intent to handler in _handle_intent method in src/ara/router/orchestrator.py
- [x] T027 [US2] Update _generate_countdown_phrase to use cached user name in src/ara/router/orchestrator.py

**Checkpoint**: Countdown uses personalized name when configured

---

## Phase 5: User Story 3 - Concise Tone (Priority: P3)

**Goal**: Assistant responses are friendly but brief, without excessive verbosity

**Independent Test**: Set a reminder and verify confirmation is one clear sentence without filler phrases

### Tests for User Story 3

- [x] T028 [P] [US3] Unit test for concise reminder confirmation response format in tests/unit/test_personality_responses.py
- [x] T029 [P] [US3] Unit test for concise reminder list response format in tests/unit/test_personality_responses.py

### Implementation for User Story 3

- [x] T030 [US3] Update DEFAULT_PERSONALITY.system_prompt to remove "playful" and "witty" emphasis in src/ara/config/personality.py
- [x] T031 [US3] Add explicit brevity instruction "Keep responses to one sentence when possible" in src/ara/config/personality.py
- [x] T032 [US3] Add bad/good examples to system prompt (verbose vs concise) in src/ara/config/personality.py
- [x] T033 [US3] Update _handle_reminder_set response format for concise confirmation in src/ara/router/orchestrator.py
- [x] T034 [US3] Update _handle_reminder_query response format for concise listing in src/ara/router/orchestrator.py
- [x] T035 [US3] Update _handle_reminder_cancel response format for concise confirmation in src/ara/router/orchestrator.py
- [x] T036 [US3] Update _handle_reminder_clear_all response format for concise confirmation in src/ara/router/orchestrator.py

**Checkpoint**: All responses are friendly but concise

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Integration testing, documentation, and validation

- [x] T037 [P] Integration test for complete countdown flow in tests/integration/test_countdown_flow.py
- [x] T038 [P] Integration test for countdown cancellation mid-countdown in tests/integration/test_countdown_flow.py
- [x] T039 [P] Integration test for overlapping timers combined countdown in tests/integration/test_countdown_flow.py
- [x] T040 Update voice command reference documentation with countdown behavior in specs/003-timer-countdown/contracts/voice-commands.md
- [x] T041 Run quickstart.md validation scenarios manually (automated tests pass, manual hardware testing pending)
- [x] T042 Mark feature tasks complete and update spec status to "Implemented"

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - US1 can start immediately after Foundational
  - US2 can start after Foundational (independent of US1)
  - US3 can start after Foundational (independent of US1/US2)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Uses countdown phrase from US1 but tests name feature independently
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Completely independent of US1/US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core logic before edge case handling
- Story complete before moving to next priority

### Parallel Opportunities

- T002 can run in parallel with Setup verification
- T003, T004, T005 can all run in parallel (different functions in same file)
- All tests for a user story marked [P] can run in parallel
- US1, US2, US3 can be worked on in parallel after Foundational phase (if team capacity allows)

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for countdown phrase generation in tests/unit/test_countdown.py"
Task: "Unit test for countdown timing accuracy in tests/unit/test_countdown.py"
Task: "Unit test for short timer handling in tests/unit/test_countdown.py"
Task: "Unit test for overlapping countdown combination in tests/unit/test_countdown.py"
```

---

## Parallel Example: User Story 2 Implementation

```bash
# Intent changes can be done in parallel with orchestrator changes:
Task: "Add USER_NAME_SET intent type in src/ara/router/intent.py"  # T021-T023
# Then sequentially:
Task: "Load user profile in Orchestrator.__init__"  # T024
Task: "Add handler and wire to _handle_intent"  # T025-T026
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test countdown with "Hey" address
5. Deploy/demo if ready - countdown works without personalization

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Countdown works with "Hey" → Demo (MVP!)
3. Add User Story 2 → Countdown uses name → Demo
4. Add User Story 3 → Concise responses → Demo
5. Each story adds value without breaking previous stories

### Single Developer Strategy

1. Complete Setup + Foundational
2. User Story 1 (P1) → Test → Checkpoint
3. User Story 2 (P2) → Test → Checkpoint
4. User Story 3 (P3) → Test → Checkpoint
5. Polish phase → Final validation

---

## Notes

- [P] tasks = different files or independent functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Pre-synthesize countdown numbers at startup for timing accuracy (from research.md)
