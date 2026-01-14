# Tasks: Warm Personality with Timer/Reminder System

**Input**: Design documents from `/specs/002-personality-timers/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests included per Constitution Principle V (Test-Driven Development)

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/ara/`, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and personality configuration infrastructure

- [x] T001 Create PersonalityConfig dataclass in src/ara/config/personality.py
- [x] T002 [P] Add default Purcobine system prompt to src/ara/config/personality.py
- [x] T003 [P] Create ~/.ara/ directory utility function in src/ara/config/loader.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core persistence infrastructure that MUST be complete before user story implementation

**Note**: Existing timer/reminder system already works. This phase adds persistence layer.

- [x] T004 Add persistence_path parameter to ReminderManager.__init__ in src/ara/commands/reminder.py
- [x] T005 Implement _save() method for JSON serialization in src/ara/commands/reminder.py
- [x] T006 Implement _load() method for JSON deserialization in src/ara/commands/reminder.py
- [x] T007 Add save calls after create, cancel, dismiss, trigger in src/ara/commands/reminder.py
- [x] T008 Create local time formatting utility in src/ara/commands/reminder.py

**Checkpoint**: Persistence infrastructure ready - user story implementation can begin

---

## Phase 3: User Story 1 - Set a Reminder with Voice Command (Priority: P1) MVP

**Goal**: Users can set reminders and receive time-aware confirmations showing both current time and target time

**Independent Test**: Say "remind me in 5 minutes to check the oven" and verify response includes "It's X:XX now, I'll remind you at Y:YY"

### Tests for User Story 1

> **Write tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Unit test for time-aware response formatting in tests/unit/test_reminder_time_format.py
- [x] T010 [P] [US1] Unit test for reminder creation with persistence in tests/unit/test_reminder_persistence.py
- [x] T011 [P] [US1] Integration test for reminder set flow in tests/integration/test_reminder_flow.py

### Implementation for User Story 1

- [x] T012 [US1] Modify _handle_reminder_set() to include current time in response in src/ara/router/orchestrator.py
- [x] T013 [US1] Update response format to "Got it! It's X:XX now, I'll remind you at Y:YY to [task]" in src/ara/router/orchestrator.py
- [x] T014 [US1] Add local timezone display conversion in src/ara/router/orchestrator.py
- [x] T015 [US1] Update ReminderManager initialization with persistence path in src/ara/router/orchestrator.py
- [x] T016 [US1] Verify reminder confirmation shows both times correctly
- [x] T017 [US1] Add validation to reject zero/negative durations with warm message in src/ara/router/orchestrator.py

**Checkpoint**: User Story 1 complete - reminders can be set with time-aware confirmations

---

## Phase 4: User Story 2 - Manage Multiple Concurrent Reminders (Priority: P2)

**Goal**: Multiple reminders can be set simultaneously without overwriting each other, and all persist correctly

**Independent Test**: Set 3 reminders in sequence, restart assistant, verify all 3 are restored

**Note**: Multiple concurrent reminders already supported. This ensures persistence works for multiple.

### Tests for User Story 2

- [x] T018 [P] [US2] Unit test for multiple reminder persistence in tests/unit/test_reminder_persistence.py
- [x] T019 [P] [US2] Integration test for concurrent reminder handling in tests/integration/test_reminder_flow.py

### Implementation for User Story 2

- [x] T020 [US2] Verify _save() correctly serializes multiple reminders in src/ara/commands/reminder.py
- [x] T021 [US2] Verify _load() correctly deserializes multiple reminders in src/ara/commands/reminder.py
- [x] T022 [US2] Add test for 10+ concurrent reminders without degradation

**Checkpoint**: Multiple reminders persist and restore correctly across restarts

---

## Phase 5: User Story 3 - List Active Reminders with Numbered Format (Priority: P3)

**Goal**: Users can ask to list all active reminders in numbered format (first, second, third...) for easy reference

**Independent Test**: Set 3 reminders, ask "what reminders do I have", verify all listed with ordinal numbers (first, second, third) and times

**Note**: List functionality exists. Update to use numbered format per contracts.

### Tests for User Story 3

- [x] T023 [P] [US3] Unit test for numbered reminder list formatting in tests/unit/test_personality_responses.py
- [x] T024 [P] [US3] Unit test for ordinal number generation (first through tenth, then 11th+) in tests/unit/test_reminder_formatting.py

### Implementation for User Story 3

- [x] T025 [US3] Create ordinal number utility function (first, second... 11th, 12th) in src/ara/router/orchestrator.py
- [x] T026 [US3] Update _handle_reminder_query() to format with numbered list in src/ara/router/orchestrator.py
- [x] T027 [US3] Format: "First, you have a reminder at X:XX AM to [task]. Second, ..." in src/ara/router/orchestrator.py
- [x] T028 [US3] Update response for single reminder with warm language in src/ara/router/orchestrator.py
- [x] T029 [US3] Update "no reminders" response to "Your schedule is clear" in src/ara/router/orchestrator.py
- [x] T030 [US3] Ensure chronological sort order for consistent numbering in src/ara/router/orchestrator.py

**Checkpoint**: Reminder listing uses numbered format with warm language

---

## Phase 6: User Story 4 - Warm, Playful, and Witty Personality (Priority: P4)

**Goal**: Configure Purcobine personality via system prompt so all LLM responses reflect warmth, playfulness, and wit

**Independent Test**: Have any conversation and verify responses are warm/friendly (not robotic)

### Tests for User Story 4

- [x] T031 [P] [US4] Unit test for personality config loading in tests/unit/test_personality_responses.py
- [x] T032 [P] [US4] Integration test for system prompt application in tests/integration/test_personality.py

### Implementation for User Story 4

- [x] T033 [US4] Load PersonalityConfig in orchestrator initialization in src/ara/router/orchestrator.py
- [x] T034 [US4] Call llm.set_system_prompt() with Purcobine prompt in src/ara/router/orchestrator.py
- [x] T035 [US4] Update timer response strings with warm language in src/ara/router/orchestrator.py
- [x] T036 [US4] Update error/clarification responses to be gentle and encouraging in src/ara/router/orchestrator.py

**Checkpoint**: All assistant responses reflect Purcobine's warm personality

---

## Phase 7: User Story 5 - Cancel Reminders by Description or Number (Priority: P5)

**Goal**: Users can cancel reminders by description, by number, or cancel multiple reminders at once

**Independent Test**: Set 5 reminders, cancel "reminder number 3", verify only that reminder is removed

**Note**: Cancel functionality exists. Extend to support cancel by number and multiple numbers.

### Tests for User Story 5

- [x] T037 [P] [US5] Unit test for cancel by description in tests/unit/test_reminder_persistence.py
- [x] T038 [P] [US5] Unit test for cancel by single number in tests/unit/test_reminder_cancel.py
- [x] T039 [P] [US5] Unit test for cancel by multiple numbers in tests/unit/test_reminder_cancel.py
- [x] T040 [P] [US5] Unit test for invalid number handling in tests/unit/test_reminder_cancel.py

### Implementation for User Story 5

- [x] T041 [US5] Extend intent patterns to recognize "delete reminder number N" in src/ara/router/intent.py
- [x] T042 [US5] Extend intent patterns to recognize ordinal forms ("third reminder") in src/ara/router/intent.py
- [x] T043 [US5] Add number extraction for multiple numbers ("2, 4, and 5") in src/ara/router/intent.py
- [x] T044 [US5] Modify _handle_reminder_cancel() to support cancel by index in src/ara/router/orchestrator.py
- [x] T045 [US5] Add validation for out-of-range numbers in src/ara/router/orchestrator.py
- [x] T046 [US5] Implement multiple number cancellation in single command in src/ara/router/orchestrator.py
- [x] T047 [US5] Update response to confirm which reminder(s) cancelled with details in src/ara/router/orchestrator.py
- [x] T048 [US5] Update ambiguous cancel response to suggest numbered list in src/ara/router/orchestrator.py
- [x] T049 [US5] Verify _save() called after cancel operation

**Checkpoint**: Reminder cancellation works by description, number, or multiple numbers

---

## Phase 8: User Story 6 - Clear All Reminders (Priority: P6)

**Goal**: Users can clear all reminders at once with a single command

**Independent Test**: Set 5 reminders, say "clear all reminders", verify all are removed and response shows count

### Tests for User Story 6

- [x] T050 [P] [US6] Unit test for clear all with count confirmation in tests/unit/test_reminder_clear.py
- [x] T051 [P] [US6] Unit test for clear all when empty in tests/unit/test_reminder_clear.py

### Implementation for User Story 6

- [x] T052 [US6] Add REMINDER_CLEAR_ALL to IntentType enum in src/ara/router/intent.py
- [x] T053 [US6] Add intent patterns for "clear all reminders", "delete all my reminders" in src/ara/router/intent.py
- [x] T054 [US6] Implement clear_all() method in ReminderManager in src/ara/commands/reminder.py
- [x] T055 [US6] Add _handle_reminder_clear_all() handler in src/ara/router/orchestrator.py
- [x] T056 [US6] Response includes count: "Done! I've cleared all N of your reminders." in src/ara/router/orchestrator.py
- [x] T057 [US6] Handle empty case: "You don't have any reminders to clear" in src/ara/router/orchestrator.py

**Checkpoint**: Clear all reminders command works with count confirmation

---

## Phase 9: Missed Reminder Handling (Edge Case)

**Goal**: Reminders that triggered during system downtime are delivered immediately on startup

**Independent Test**: Set reminder for 1 minute, stop assistant, wait 2 minutes, restart, verify reminder delivered with explanation

### Tests for Missed Reminders

- [x] T058 [P] Unit test for missed reminder detection in tests/unit/test_reminder_persistence.py
- [x] T059 [P] Integration test for missed reminder delivery in tests/integration/test_reminder_flow.py

### Implementation for Missed Reminders

- [x] T060 Implement check_missed() method in ReminderManager in src/ara/commands/reminder.py
- [x] T061 Call check_missed() on orchestrator startup in src/ara/router/orchestrator.py
- [x] T062 Format missed reminder response per contracts in src/ara/router/orchestrator.py

**Checkpoint**: Missed reminders are caught and delivered on restart

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and final validation

- [x] T063 Update voice command reference documentation in ara-voice-assistant-pi4-setup.md
- [x] T064 Run all tests and verify passing
- [x] T065 Run quickstart.md validation scenarios
- [x] T066 Code cleanup and lint check with ruff

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
- **Missed Reminders (Phase 9)**: Depends on Phase 2 (persistence)
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational only - MVP deliverable
- **User Story 2 (P2)**: Depends on US1 (uses same persistence) - but can be tested independently
- **User Story 3 (P3)**: No dependency on other stories - numbered list formatting
- **User Story 4 (P4)**: No dependency on other stories - personality config only
- **User Story 5 (P5)**: Depends on US3 (uses numbered list for cancel by number)
- **User Story 6 (P6)**: No dependency on other stories - clear all is independent

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation follows tests
- Verify at checkpoint before moving to next story

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002 [P] - Add default Purcobine system prompt
T003 [P] - Create ~/.ara/ directory utility
```

**Phase 3 (US1 Tests)**:
```
T009 [P] - Unit test for time-aware formatting
T010 [P] - Unit test for persistence
T011 [P] - Integration test for flow
```

**Phase 5 (US3 Tests)**:
```
T023 [P] - Unit test for numbered list formatting
T024 [P] - Unit test for ordinal number generation
```

**Phase 7 (US5 Tests)**:
```
T037-T040 [P] - All cancel tests can run in parallel
```

**User Stories 3, 4, 6** can be developed in parallel after Foundational is complete (different functionality).

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together:
Task: "Unit test for time-aware response formatting in tests/unit/test_reminder_time_format.py"
Task: "Unit test for reminder creation with persistence in tests/unit/test_reminder_persistence.py"
Task: "Integration test for reminder set flow in tests/integration/test_reminder_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (persistence layer)
3. Complete Phase 3: User Story 1 (time-aware reminders)
4. **STOP and VALIDATE**: Test time-aware confirmations work
5. Deploy/demo if ready - basic reminder functionality complete

### Incremental Delivery

1. Setup + Foundational → Persistence ready
2. Add User Story 1 → Time-aware confirmations → Demo (MVP!)
3. Add User Story 4 → Warm personality → Demo
4. Add User Stories 2, 3, 5, 6 → Complete reminder management (including clear all)
5. Add Phase 9 → Missed reminder handling
6. Each story adds value without breaking previous stories

### Single Developer Strategy

Execute phases sequentially:
1. Phase 1 → Phase 2 → Foundation ready
2. Phase 3 (US1) → Validate → MVP done
3. Phase 6 (US4) → Personality enabled
4. Phases 4, 5, 7, 8 → Complete features (including cancel by number, clear all)
5. Phase 9 → Edge cases (missed reminders)
6. Phase 10 → Polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Existing timer/reminder code is extended, not replaced
- Personality affects LLM responses; command responses updated manually
- JSON persistence is synchronous (fast enough for <100 reminders)
- All times stored UTC, displayed in local timezone
- Ordinal numbers: "first" through "tenth", then "11th", "12th", etc.
- Cancel by number references chronologically-sorted list order
- Clear all reminders returns count of cleared items for confirmation
