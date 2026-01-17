# Tasks: Passive Speech Interrupt and Reprocessing

**Input**: Design documents from `/specs/008-passive-speech-reprocess/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per Constitution Principle V (Test-Driven Development)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/ara/`, `tests/` at repository root

---

## Phase 1: Setup

**Purpose**: Project initialization - extend existing audio infrastructure

- [x] T001 Add `is_playing` property to AudioPlayback protocol in src/ara/audio/playback.py
- [x] T002 [P] Implement `is_playing` property in macOS backend in src/ara/audio/backends/macos.py
- [x] T003 [P] Implement `is_playing` property in Linux backend in src/ara/audio/backends/linux.py
- [x] T004 Add interrupt acknowledgment tone method to src/ara/feedback/audio.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core interrupt infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (TDD per Constitution)

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] Unit test for InterruptState enum in tests/unit/test_interrupt.py
- [x] T006 [P] Unit test for BufferSegment dataclass in tests/unit/test_interrupt.py
- [x] T007 [P] Unit test for RequestBuffer class in tests/unit/test_interrupt.py
- [x] T008 [P] Unit test for ContinuationWindow class in tests/unit/test_interrupt.py
- [x] T009 Unit test for InterruptManager state transitions in tests/unit/test_interrupt.py

### Implementation for Foundational

- [x] T010 Create interrupt module with InterruptState enum in src/ara/router/interrupt.py
- [x] T011 Implement BufferSegment dataclass in src/ara/router/interrupt.py
- [x] T012 Implement RequestBuffer class with append/get_combined_text/clear in src/ara/router/interrupt.py
- [x] T013 Implement ContinuationWindow class with start/cancel/reset/is_active in src/ara/router/interrupt.py
- [x] T014 Implement InterruptManager class skeleton with state property in src/ara/router/interrupt.py
- [x] T015 Add constants (INTERRUPT_THRESHOLD, SILENCE_TIMEOUT_MS, etc.) to src/ara/router/interrupt.py

**Checkpoint**: Foundation ready - all data structures and state machine in place

---

## Phase 3: User Story 1 - Append Additional Context During Response (Priority: P1) 🎯 MVP

**Goal**: User can interrupt agent mid-response to add context; agent combines input and reprocesses

**Independent Test**: Say "Research BSI", let agent respond, say "add it to my action items" → agent interprets as "add Research BSI to action items"

### Tests for User Story 1

- [x] T016 [P] [US1] Unit test for play_with_monitoring detecting interrupt in tests/unit/test_interrupt.py
- [x] T017 [P] [US1] Unit test for wait_for_interrupt_complete with 2s silence in tests/unit/test_interrupt.py
- [x] T018 [US1] Integration test for interrupt flow in tests/integration/test_interrupt_flow.py

### Implementation for User Story 1

- [x] T019 [US1] Implement start_monitoring method in InterruptManager in src/ara/router/interrupt.py
- [x] T020 [US1] Implement stop_monitoring method in InterruptManager in src/ara/router/interrupt.py
- [x] T021 [US1] Implement play_with_monitoring method (parallel capture during playback) in src/ara/router/interrupt.py
- [x] T022 [US1] Implement wait_for_interrupt_complete method (2s silence detection) in src/ara/router/interrupt.py
- [x] T023 [US1] Implement get_combined_request method in src/ara/router/interrupt.py
- [x] T024 [US1] Add energy-based VAD with 750 threshold in play_with_monitoring in src/ara/router/interrupt.py
- [x] T025 [US1] Integrate InterruptManager into Orchestrator.__init__ in src/ara/router/orchestrator.py
- [x] T026 [US1] Modify Orchestrator voice loop to use play_with_monitoring for TTS in src/ara/router/orchestrator.py
- [x] T027 [US1] Add interrupt handling branch in voice loop (stop TTS, record interrupt, reprocess) in src/ara/router/orchestrator.py
- [x] T028 [US1] Play interrupt acknowledgment tone when interrupt detected in src/ara/router/orchestrator.py

**Checkpoint**: User Story 1 complete - can interrupt mid-response and have input combined

---

## Phase 4: User Story 2 - Modify Request with Additional Details (Priority: P1)

**Goal**: User can add qualifiers (location, time) mid-response to modify the original request

**Independent Test**: Say "Research BSI", agent responds, say "in Austin" → agent understands "Research BSI in Austin"

### Tests for User Story 2

- [x] T029 [P] [US2] Unit test for multiple sequential interrupts in tests/unit/test_interrupt.py
- [x] T030 [US2] Integration test for additive interrupt scenario in tests/integration/test_interrupt_flow.py

### Implementation for User Story 2

- [x] T031 [US2] Ensure RequestBuffer supports unlimited appends in src/ara/router/interrupt.py
- [x] T032 [US2] Add logic to detect rapid sequential interrupts and accumulate before reprocessing in src/ara/router/interrupt.py
- [x] T033 [US2] Verify space-concatenation produces natural language in get_combined_text in src/ara/router/interrupt.py

**Checkpoint**: User Stories 1 AND 2 complete - users can append context or add details

---

## Phase 5: User Story 3 - Post-Response Continuation Window (Priority: P2)

**Goal**: 5-second grace period after response where user input is treated as continuation

**Independent Test**: Ask "What's the weather", agent responds, say "and tomorrow" within 5s → agent provides both days

### Tests for User Story 3

- [x] T034 [P] [US3] Unit test for continuation window timing (5s expiry) in tests/unit/test_interrupt.py
- [x] T035 [P] [US3] Unit test for continuation window cancel on user speech in tests/unit/test_interrupt.py
- [x] T036 [US3] Integration test for continuation window flow in tests/integration/test_interrupt_flow.py

### Implementation for User Story 3

- [x] T037 [US3] Implement start_continuation_window in InterruptManager in src/ara/router/interrupt.py
- [x] T038 [US3] Implement cancel_continuation_window in InterruptManager in src/ara/router/interrupt.py
- [x] T039 [US3] Add continuation window check in Orchestrator after TTS completes in src/ara/router/orchestrator.py
- [x] T040 [US3] Add state transition RESPONDING → CONTINUATION when playback finishes without interrupt in src/ara/router/interrupt.py
- [x] T041 [US3] Add state transition CONTINUATION → INTERRUPTED when user speaks in window in src/ara/router/interrupt.py
- [x] T042 [US3] Add state transition CONTINUATION → IDLE on 5s timeout (reset buffer) in src/ara/router/interrupt.py

**Checkpoint**: User Stories 1, 2, AND 3 complete - full continuation flow working

---

## Phase 6: User Story 4 - Change Intent Entirely (Priority: P2)

**Goal**: User can redirect agent completely mid-response ("actually, show my calendar")

**Independent Test**: Say "Tell me about Python", agent responds, say "actually, what's on my calendar" → agent shows calendar

### Tests for User Story 4

- [x] T043 [P] [US4] Unit test for special keywords (stop, wait, cancel, never mind) in tests/unit/test_interrupt.py
- [x] T044 [US4] Integration test for intent redirect scenario in tests/integration/test_interrupt_flow.py

### Implementation for User Story 4

- [x] T045 [US4] Add special keyword detection for "stop", "wait", "cancel", "never mind" in src/ara/router/interrupt.py
- [x] T046 [US4] Implement pause-and-wait behavior for "stop"/"wait" keywords in src/ara/router/orchestrator.py
- [x] T047 [US4] Add clarification request when intent is ambiguous/contradictory in src/ara/router/orchestrator.py
- [x] T048 [US4] Ensure RequestBuffer preserves context even after clarification request in src/ara/router/interrupt.py

**Checkpoint**: All user stories complete - full interrupt functionality

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, cleanup, benchmarking

- [ ] T049 [P] Add interrupt behavior to voice command documentation in docs/
- [ ] T050 [P] Run benchmark for TTS stop latency on Raspberry Pi 4
- [ ] T051 [P] Run benchmark for reprocessing latency on Raspberry Pi 4
- [x] T052 Verify all tests pass with `pytest tests/unit/test_interrupt.py tests/integration/test_interrupt_flow.py`
- [x] T053 Code review for thread safety (locks, events, timer cleanup)
- [x] T054 Update quickstart.md validation checklist in specs/008-passive-speech-reprocess/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational completion
  - US1 and US2 are both P1 - implement in sequence (US1 first, US2 extends)
  - US3 and US4 are both P2 - can proceed after US1/US2 complete
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

| Story | Priority | Dependencies | Notes |
|-------|----------|--------------|-------|
| US1 | P1 | Foundational | Core interrupt flow - MVP |
| US2 | P1 | US1 | Extends US1 with multi-interrupt support |
| US3 | P2 | US1 | Adds continuation window |
| US4 | P2 | US1 | Adds special keyword handling |

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD)
2. InterruptManager methods before Orchestrator integration
3. State transitions before orchestrator usage
4. Verify tests pass after implementation

### Parallel Opportunities

**Phase 1 (Setup)**:
```
T002 (macos.py) ║ T003 (linux.py) - different files
```

**Phase 2 (Foundational)**:
```
T005 ║ T006 ║ T007 ║ T008 - different test functions
```

**Phase 3 (US1)**:
```
T016 ║ T017 - different test functions
```

**Phase 5 (US3)**:
```
T034 ║ T035 - different test functions
```

---

## Parallel Example: Foundational Tests

```bash
# Launch all foundational tests in parallel:
Task: "Unit test for InterruptState enum in tests/unit/test_interrupt.py"
Task: "Unit test for BufferSegment dataclass in tests/unit/test_interrupt.py"
Task: "Unit test for RequestBuffer class in tests/unit/test_interrupt.py"
Task: "Unit test for ContinuationWindow class in tests/unit/test_interrupt.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T015)
3. Complete Phase 3: User Story 1 (T016-T028)
4. **STOP and VALIDATE**: Test interrupt detection and reprocessing
5. Deploy MVP if US1 is sufficient

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add User Story 1 → Basic interrupt works → **MVP**
3. Add User Story 2 → Multi-interrupt works → Enhanced
4. Add User Story 3 → Continuation window works → Polished
5. Add User Story 4 → Special keywords work → Complete
6. Polish → Documentation, benchmarks → Production-ready

### Sequential Recommendation

Given this is a single-developer effort on a voice assistant:

1. **Week 1**: Setup + Foundational + US1 (MVP functional)
2. **Week 2**: US2 + US3 (natural conversation flow)
3. **Week 3**: US4 + Polish (complete feature)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story should be independently testable after completion
- Verify tests fail before implementing (TDD per Constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Benchmark on Raspberry Pi 4 (target hardware) before completion
