# Tasks: Claude Query Mode

**Input**: Design documents from `/specs/009-claude-query-mode/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/claude-module.md, research.md, quickstart.md

**Tests**: Test tasks are included as the spec mentions TDD (Test-Driven Development principle in constitution).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create claude module structure and foundational types

- [x] T001 Create claude module directory structure at src/ara/claude/
- [x] T002 [P] Create claude module __init__.py with exports in src/ara/claude/__init__.py
- [x] T003 [P] Create error types (ClaudeError, ClaudeTimeoutError, ClaudeAPIError, ClaudeAuthError, ClaudeConnectivityError) in src/ara/claude/errors.py
- [x] T004 [P] Add CLAUDE_WAITING to FeedbackType enum in src/ara/feedback/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Add ClaudeClientConfig dataclass with from_env() in src/ara/claude/client.py
- [x] T006 Add CLAUDE_QUERY, CLAUDE_SUMMARY, CLAUDE_RESET to IntentType enum in src/ara/router/intent.py
- [x] T007 [P] Create ClaudeRepository class skeleton in src/ara/storage/claude_repository.py
- [x] T008 [P] Create test file skeleton for unit tests in tests/unit/test_claude_intent.py
- [x] T009 [P] Create test file skeleton for contract tests in tests/contract/test_claude_storage.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Basic Claude Query (Priority: P1) 🎯 MVP

**Goal**: User can say "ask Claude [question]" and receive a spoken response

**Independent Test**: Say "ask Claude what is the capital of France" and hear Claude's answer

### Tests for User Story 1

- [x] T010 [P] [US1] Unit test for CLAUDE_QUERY intent patterns in tests/unit/test_claude_intent.py
- [x] T011 [P] [US1] Unit test for ClaudeClient.send_message() in tests/unit/test_claude_client.py
- [x] T012 [P] [US1] Contract test for ClaudeRepository.save_query() and save_response() in tests/contract/test_claude_storage.py

### Implementation for User Story 1

- [x] T013 [US1] Add CLAUDE_QUERY_PATTERNS to IntentClassifier in src/ara/router/intent.py
- [x] T014 [US1] Implement _try_claude_query() method in IntentClassifier in src/ara/router/intent.py
- [x] T015 [US1] Implement ClaudeClient with send_message() and check_connectivity() in src/ara/claude/client.py
- [x] T016 [US1] Implement ClaudeRepository.save_query() method in src/ara/storage/claude_repository.py
- [x] T017 [US1] Implement ClaudeRepository.save_response() method in src/ara/storage/claude_repository.py
- [x] T018 [US1] Create ClaudeHandler with handle_query() method in src/ara/claude/handler.py
- [x] T019 [US1] Integrate ClaudeHandler with orchestrator in src/ara/router/orchestrator.py
- [x] T020 [US1] Add system prompt for concise responses (~150 words) in src/ara/claude/client.py

**Checkpoint**: User Story 1 complete - basic query/response works independently

---

## Phase 4: User Story 2 - Waiting Feedback (Priority: P2)

**Goal**: Musical loop plays while waiting for Claude's response

**Independent Test**: Ask Claude a question, verify musical loop plays until response arrives

### Tests for User Story 2

- [x] T021 [P] [US2] Unit test for WaitingIndicator start/stop behavior in tests/unit/test_waiting_indicator.py

### Implementation for User Story 2

- [x] T022 [US2] Create WaitingIndicator class with start(), stop(), is_playing in src/ara/feedback/waiting.py
- [x] T023 [US2] Create or source musical loop audio file at assets/sounds/claude_waiting.wav (uses generated tone as fallback)
- [x] T024 [US2] Add CLAUDE_WAITING sound configuration to SoundFeedback in src/ara/feedback/audio.py
- [x] T025 [US2] Integrate WaitingIndicator into ClaudeHandler.handle_query() in src/ara/claude/handler.py

**Checkpoint**: User Story 2 complete - audio feedback works during query wait

---

## Phase 5: User Story 3 - Follow-up Questions (Priority: P2)

**Goal**: 5-second window after response for follow-up questions without trigger phrase

**Independent Test**: Ask Claude a question, then ask follow-up within 5 seconds without "ask Claude"

### Tests for User Story 3

- [x] T026 [P] [US3] Unit test for ClaudeSession message management in tests/unit/test_claude_session.py
- [x] T027 [P] [US3] Unit test for follow-up window timing in tests/unit/test_claude_session.py

### Implementation for User Story 3

- [x] T028 [US3] Implement ClaudeSession class with message history in src/ara/claude/session.py
- [x] T029 [US3] Add add_user_message() and add_assistant_message() methods in src/ara/claude/session.py
- [x] T030 [US3] Add get_api_messages() method for Claude API format in src/ara/claude/session.py
- [x] T031 [US3] Add reset() method for conversation clearing in src/ara/claude/session.py
- [x] T032 [US3] Integrate ClaudeSession with ClaudeClient for context in src/ara/claude/client.py
- [x] T033 [US3] Add 5-second follow-up window detection in ClaudeHandler in src/ara/claude/handler.py
- [x] T034 [US3] Wire follow-up detection into orchestrator flow in src/ara/router/orchestrator.py

**Checkpoint**: User Story 3 complete - follow-up conversations work naturally

---

## Phase 6: User Story 4 - Authentication Setup (Priority: P3)

**Goal**: One-time authentication setup that persists across restarts

**Independent Test**: Configure API key once, restart Ara, verify queries still work

### Tests for User Story 4

- [x] T035 [P] [US4] Unit test for ClaudeClientConfig.from_env() in tests/unit/test_claude_client.py

### Implementation for User Story 4

- [x] T036 [US4] Add ANTHROPIC_API_KEY loading from environment in src/ara/claude/client.py
- [x] T037 [US4] Add API key validation on first query attempt in src/ara/claude/client.py
- [x] T038 [US4] Add "please set up authentication" prompt when missing in src/ara/claude/handler.py
- [x] T039 [US4] Update config documentation in config/base.yaml for Claude settings

**Checkpoint**: User Story 4 complete - authentication configured and persists

---

## Phase 7: User Story 5 - Query History Summarization (Priority: P3)

**Goal**: User can ask for summaries of Claude conversations by time period

**Independent Test**: Ask several questions, then "summarize my Claude conversations today"

### Tests for User Story 5

- [x] T040 [P] [US5] Unit test for CLAUDE_SUMMARY intent patterns in tests/unit/test_claude_intent.py
- [x] T041 [P] [US5] Contract test for ClaudeRepository.get_queries_by_date_range() in tests/contract/test_claude_storage.py

### Implementation for User Story 5

- [x] T042 [US5] Add CLAUDE_SUMMARY_PATTERNS to IntentClassifier in src/ara/router/intent.py
- [x] T043 [US5] Implement _try_claude_summary() method in IntentClassifier in src/ara/router/intent.py
- [x] T044 [US5] Implement ClaudeRepository.get_queries_by_date_range() in src/ara/storage/claude_repository.py
- [x] T045 [US5] Implement ClaudeRepository.get_response_for_query() in src/ara/storage/claude_repository.py
- [x] T046 [US5] Implement ClaudeRepository.get_conversations_for_period() in src/ara/storage/claude_repository.py
- [x] T047 [US5] Implement ClaudeHandler.handle_summary_request() in src/ara/claude/handler.py
- [x] T048 [US5] Wire CLAUDE_SUMMARY intent to handler in orchestrator in src/ara/router/orchestrator.py

**Checkpoint**: User Story 5 complete - time-based summaries work

---

## Phase 8: User Story 6 - Error Handling (Priority: P4)

**Goal**: Clear spoken feedback for all error conditions

**Independent Test**: Simulate network failure, verify friendly error message is spoken

### Tests for User Story 6

- [x] T049 [P] [US6] Unit test for connectivity check in tests/unit/test_claude_client.py
- [x] T050 [P] [US6] Unit test for timeout handling in tests/unit/test_claude_client.py

### Implementation for User Story 6

- [x] T051 [US6] Add CLAUDE_RESET_PATTERNS to IntentClassifier in src/ara/router/intent.py
- [x] T052 [US6] Implement _try_claude_reset() method in IntentClassifier in src/ara/router/intent.py
- [x] T053 [US6] Add connectivity error handling in ClaudeHandler in src/ara/claude/handler.py
- [x] T054 [US6] Add 30-second timeout with retry prompt in ClaudeHandler in src/ara/claude/handler.py
- [x] T055 [US6] Add authentication error handling in ClaudeHandler in src/ara/claude/handler.py
- [x] T056 [US6] Implement ClaudeHandler.handle_reset() for "new conversation" in src/ara/claude/handler.py
- [x] T057 [US6] Wire CLAUDE_RESET intent to handler in orchestrator in src/ara/router/orchestrator.py

**Checkpoint**: User Story 6 complete - all error cases handled gracefully

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and validation

- [x] T058 [P] Integration test for full Claude query flow in tests/integration/test_claude_flow.py
- [x] T059 [P] Update voice command reference documentation in docs/voice-commands.md
- [x] T060 Run all tests and ensure passing: PYTHONPATH=src python -m pytest tests/ -v
- [x] T061 Run linting: ruff check src/ara/claude/ tests/unit/test_claude*.py
- [x] T062 Validate against quickstart.md scenarios manually
- [x] T063 Code review and cleanup across all new files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational completion
  - US1 (P1): Foundation → MVP delivery
  - US2 (P2): Foundation → can parallel with US3
  - US3 (P2): Foundation → can parallel with US2
  - US4 (P3): Foundation (note: US1 implicitly uses config)
  - US5 (P3): Foundation + US1 (needs saved queries)
  - US6 (P4): Foundation
- **Polish (Phase 9)**: Depends on all desired stories complete

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 (Basic Query) | Foundational | None - start first |
| US2 (Waiting Feedback) | Foundational | US3, US4, US6 |
| US3 (Follow-ups) | Foundational | US2, US4, US6 |
| US4 (Auth Setup) | Foundational | US2, US3, US6 |
| US5 (Summarization) | Foundational, US1 (needs saved data) | US6 |
| US6 (Error Handling) | Foundational | US2, US3, US4 |

### Parallel Opportunities

**Within Phase 1 (Setup)**:
- T002, T003, T004 can run in parallel

**Within Phase 2 (Foundational)**:
- T007, T008, T009 can run in parallel

**Within each User Story**:
- All test tasks marked [P] can run in parallel
- Model/pattern tasks before handler integration

---

## Parallel Example: User Story 1

```bash
# Launch all tests for US1 together:
Task: "Unit test for CLAUDE_QUERY intent patterns" (T010)
Task: "Unit test for ClaudeClient.send_message()" (T011)
Task: "Contract test for ClaudeRepository" (T012)

# Then implement in sequence:
Task: "Add CLAUDE_QUERY_PATTERNS" (T013)
Task: "Implement _try_claude_query()" (T014)
# ... etc
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T009)
3. Complete Phase 3: User Story 1 (T010-T020)
4. **STOP and VALIDATE**: Test "ask Claude what is the capital of France"
5. Deploy/demo MVP

### Incremental Delivery

1. Setup + Foundational → Framework ready
2. Add US1 → Test → Deploy (MVP! Core query works)
3. Add US2 + US3 → Test → Deploy (Nice UX with waiting sound + follow-ups)
4. Add US4 → Test → Deploy (Authentication prompts)
5. Add US5 → Test → Deploy (History summarization)
6. Add US6 → Test → Deploy (Graceful error handling)
7. Polish → Final validation

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 (User Story 1)**
- 20 tasks total for functional MVP
- Delivers core value: ask Claude questions via voice
- Can be tested independently
- ~1-2 days implementation effort

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- MongoDB indexes created automatically on first repository use
