# Tasks: Email Action Items

**Input**: Design documents from `/specs/007-email-action-items/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per constitution (Principle V: Test-Driven Development)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Email Module Infrastructure)

**Purpose**: Create email module structure and configuration

- [ ] T001 Create email module directory structure at src/ara/email/
- [ ] T002 [P] Create src/ara/email/__init__.py with module exports
- [ ] T003 [P] Add EMAIL_ADDRESS, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS to .env.example

---

## Phase 2: Foundational (Core Email Infrastructure)

**Purpose**: EmailConfig and EmailResult classes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 [P] Write unit test for EmailConfig.from_env() in tests/unit/test_email_config.py
- [ ] T005 [P] Write unit test for EmailConfig.is_valid() in tests/unit/test_email_config.py
- [ ] T006 Implement EmailConfig dataclass in src/ara/email/config.py (from_env, is_valid methods)
- [ ] T007 [P] Write unit test for EmailResult factory methods in tests/unit/test_email_sender.py
- [ ] T008 Implement EmailResult dataclass in src/ara/email/sender.py (ok, not_configured, no_items, auth_failed, connection_failed, send_failed)
- [ ] T009 Add EMAIL_ACTION_ITEMS to IntentType enum in src/ara/router/intent.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Send Action Items via Voice Command (Priority: P1) 🎯 MVP

**Goal**: Users can say "email me my action items" and receive today's action items via email

**Independent Test**: Say "email me my action items" with items recorded; verify email arrives with correct list

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T010 [P] [US1] Write unit test for email body formatting (bullet list) in tests/unit/test_email_sender.py
- [ ] T011 [P] [US1] Write unit test for email subject line format in tests/unit/test_email_sender.py
- [ ] T012 [P] [US1] Write integration test for email send flow with mock SMTP in tests/integration/test_email_flow.py

### Implementation for User Story 1

- [ ] T013 [US1] Implement SMTPEmailSender.send_action_items() in src/ara/email/sender.py
- [ ] T014 [US1] Implement _format_email_body() helper in src/ara/email/sender.py
- [ ] T015 [US1] Implement _format_subject() helper in src/ara/email/sender.py
- [ ] T016 [US1] Add EMAIL_ACTION_ITEMS_PATTERNS for today's items in src/ara/router/intent.py
- [ ] T017 [US1] Add _try_email_action_items() method in IntentClassifier in src/ara/router/intent.py
- [ ] T018 [US1] Add _handle_email_action_items() handler in src/ara/router/orchestrator.py
- [ ] T019 [US1] Wire EmailSender into Orchestrator initialization in src/ara/router/orchestrator.py
- [ ] T020 [US1] Add verbal response mapping for EmailResult outcomes in src/ara/router/orchestrator.py

**Checkpoint**: User Story 1 complete - can email today's action items

---

## Phase 4: User Story 2 - Email Yesterday's Action Items (Priority: P2)

**Goal**: Users can say "email me yesterday's action items" to receive previous day's items

**Independent Test**: Say "email me yesterday's action items" with items from yesterday; verify email contains only yesterday's items

### Tests for User Story 2

- [ ] T021 [P] [US2] Write unit test for yesterday date extraction in tests/unit/test_email_sender.py
- [ ] T022 [P] [US2] Write integration test for yesterday's items email in tests/integration/test_email_flow.py

### Implementation for User Story 2

- [ ] T023 [US2] Extend EMAIL_ACTION_ITEMS_PATTERNS with "yesterday" patterns in src/ara/router/intent.py
- [ ] T024 [US2] Extract date_ref entity (today/yesterday) in _try_email_action_items() in src/ara/router/intent.py
- [ ] T025 [US2] Update _handle_email_action_items() to query correct date based on date_ref in src/ara/router/orchestrator.py
- [ ] T026 [US2] Update email subject to reflect correct date in src/ara/email/sender.py

**Checkpoint**: User Story 2 complete - can email yesterday's action items

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, documentation, and validation

- [ ] T027 [P] Add error handling for SMTP connection failures in src/ara/email/sender.py
- [ ] T028 [P] Add error handling for authentication failures in src/ara/email/sender.py
- [ ] T029 [P] Add timeout handling for SMTP operations in src/ara/email/sender.py
- [ ] T030 [P] Add logging for email send operations in src/ara/email/sender.py
- [ ] T031 Update .env documentation with email configuration variables
- [ ] T032 Run quickstart.md validation scenarios manually
- [ ] T033 Run full test suite to verify no regressions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 (Phase 4)**: Depends on Foundational phase completion (can run in parallel with US1 if staffed)
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Extends US1 patterns but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Config/models before services
- Services before orchestrator integration
- Core implementation before error handling

### Parallel Opportunities

Within Setup (Phase 1):
- T002 and T003 can run in parallel

Within Foundational (Phase 2):
- T004 and T005 can run in parallel (both config tests)
- T007 can run in parallel with config work

Within User Story 1:
- T010, T011, T012 (all tests) can run in parallel

Within User Story 2:
- T021 and T022 (both tests) can run in parallel

Within Polish:
- T027, T028, T029, T030 can all run in parallel (different error types)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Write unit test for email body formatting in tests/unit/test_email_sender.py"
Task: "Write unit test for email subject line format in tests/unit/test_email_sender.py"
Task: "Write integration test for email send flow in tests/integration/test_email_flow.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T009)
3. Complete Phase 3: User Story 1 (T010-T020)
4. **STOP and VALIDATE**: Test with "email me my action items"
5. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add Polish → Production ready

---

## Notes

- Uses Python stdlib only (smtplib, email.mime) - no external dependencies
- EmailConfig validates on load; EmailResult provides predefined error states
- Follows existing intent pattern structure from ACTION_ITEMS_QUERY
- Email is synchronous but fast (<5s typical)
- Commit after each task or logical group
