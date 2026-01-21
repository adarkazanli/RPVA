# Tasks: Platform-Adaptive Text-to-Speech

**Input**: Design documents from `/specs/010-platform-tts/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per constitution principle V (Test-Driven Development)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization - verify existing structure and dependencies

- [X] T001 Verify existing src/ara/tts/ module structure is ready for extension
- [X] T002 [P] Review existing Synthesizer protocol in src/ara/tts/synthesizer.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create Platform enum in src/ara/tts/platform.py with MACOS, RASPBERRY_PI, OTHER values
- [X] T004 Implement detect_platform() function in src/ara/tts/platform.py using platform.system() and platform.machine()
- [X] T005 [P] Write unit tests for platform detection in tests/unit/test_platform_detection.py

**Checkpoint**: Platform detection ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Transparent Platform Detection (Priority: P1) 🎯 MVP

**Goal**: Automatically select optimal TTS engine based on detected platform (macOS → native TTS, Raspberry Pi → Piper)

**Independent Test**: Run Ara on macOS and verify "Samantha" voice is used; run on Pi and verify Piper is used

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [P] [US1] Unit tests for MacOSSynthesizer in tests/unit/test_macos_synthesizer.py
- [X] T007 [P] [US1] Integration test for platform TTS selection in tests/integration/test_platform_tts.py

### Implementation for User Story 1

- [X] T008 [US1] Create MacOSSynthesizer class skeleton implementing Synthesizer protocol in src/ara/tts/macos.py
- [X] T009 [US1] Implement is_available property in MacOSSynthesizer checking for `say` command in src/ara/tts/macos.py
- [X] T010 [US1] Implement synthesize() method using subprocess.run with `say -v Samantha -o tempfile` in src/ara/tts/macos.py
- [X] T011 [US1] Implement AIFF to PCM conversion in MacOSSynthesizer._convert_aiff_to_pcm() in src/ara/tts/macos.py
- [X] T012 [US1] Implement set_voice(), set_speed(), get_available_voices() methods in src/ara/tts/macos.py
- [X] T013 [US1] Update create_synthesizer() in src/ara/tts/__init__.py to detect platform and select MacOSSynthesizer on macOS
- [X] T014 [US1] Add logging to create_synthesizer() to log which TTS engine was selected (FR-007)
- [X] T015 [US1] Export Platform and detect_platform from src/ara/tts/__init__.py

**Checkpoint**: User Story 1 complete - macOS users get native TTS, Pi users get Piper automatically

---

## Phase 4: User Story 2 - Consistent Voice Experience (Priority: P2)

**Goal**: Ensure natural, pleasant voice output on both platforms with smooth audio playback

**Independent Test**: Listen to TTS output on macOS (Samantha) and Pi (Piper); verify quality and smoothness

### Tests for User Story 2

- [X] T016 [P] [US2] Unit test for voice quality metrics (latency < 500ms) in tests/unit/test_macos_synthesizer.py
- [X] T017 [P] [US2] Integration test for audio smoothness (no glitches) in tests/integration/test_platform_tts.py

### Implementation for User Story 2

- [X] T018 [US2] Set "Samantha" as default voice in MacOSSynthesizer.__init__() in src/ara/tts/macos.py
- [X] T019 [US2] Add speed adjustment support using `say -r [rate]` parameter in src/ara/tts/macos.py
- [X] T020 [US2] Implement get_available_voices() using `say -v ?` command parsing in src/ara/tts/macos.py
- [X] T021 [US2] Verify audio sample rate (22050 Hz) matches existing playback pipeline in src/ara/tts/macos.py

**Checkpoint**: Voice quality verified - both platforms produce natural, smooth audio

---

## Phase 5: User Story 3 - Graceful Fallback (Priority: P3)

**Goal**: Implement fallback chain so system never fails silently when primary TTS unavailable

**Independent Test**: Remove `say` command access on macOS; verify fallback to Piper/Mock with warning logged

### Tests for User Story 3

- [X] T022 [P] [US3] Unit test for fallback chain in create_synthesizer() in tests/unit/test_tts.py
- [X] T023 [P] [US3] Integration test for TTS failure recovery in tests/integration/test_platform_tts.py

### Implementation for User Story 3

- [X] T024 [US3] Implement fallback chain in create_synthesizer(): macOS → Piper → Mock in src/ara/tts/__init__.py
- [X] T025 [US3] Add try/except around each synthesizer initialization in src/ara/tts/__init__.py
- [X] T026 [US3] Add logging for fallback events ("macOS TTS unavailable, falling back to Piper") in src/ara/tts/__init__.py
- [X] T027 [US3] Ensure MockSynthesizer is always available as final fallback in src/ara/tts/__init__.py
- [X] T028 [US3] Handle mid-synthesis failures gracefully in MacOSSynthesizer.synthesize() in src/ara/tts/macos.py

**Checkpoint**: All user stories complete - system never fails silently

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting all user stories

- [X] T029 [P] Run all tests and verify 100% pass rate
- [X] T030 [P] Run ruff linter and fix any issues in src/ara/tts/
- [X] T031 [P] Add type hints to all new functions in src/ara/tts/macos.py and src/ara/tts/platform.py
- [X] T032 Validate quickstart.md scenarios work end-to-end
- [X] T033 Run performance benchmark: verify TTS latency < 500ms on both platforms

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - Stories can proceed sequentially (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Foundational (T003-T005). No dependencies on other stories.
- **User Story 2 (P2)**: Depends on US1 (MacOSSynthesizer must exist). Enhances voice quality.
- **User Story 3 (P3)**: Depends on US1 (needs MacOSSynthesizer). Adds fallback handling.

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Protocol skeleton before method implementations
- Core synthesize() before helper methods
- Story complete before moving to next priority

### Parallel Opportunities

- T002 can run parallel with T001 (different files)
- T005 (tests) can run parallel with T003-T004 (implementation)
- T006, T007 can run parallel (different test files)
- T016, T017 can run parallel (different test files)
- T022, T023 can run parallel (different test files)
- T029, T030, T031 can all run parallel (different concerns)

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit tests for MacOSSynthesizer in tests/unit/test_macos_synthesizer.py"
Task: "Integration test for platform TTS selection in tests/integration/test_platform_tts.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (platform detection)
3. Complete Phase 3: User Story 1 (MacOSSynthesizer + auto-selection)
4. **STOP and VALIDATE**: Test on macOS - verify Samantha voice selected automatically
5. Test on Pi - verify Piper selected automatically
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Platform detection ready
2. Add User Story 1 → Test independently → Demo (MVP!)
3. Add User Story 2 → Test voice quality → Demo
4. Add User Story 3 → Test fallback → Deploy

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
