# Tasks: Ara Voice Assistant

**Input**: Design documents from `/specs/001-ara-voice-assistant/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per Constitution Principle V (Test-Driven Development)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Paths follow single project structure from plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependencies, and configuration structure

- [ ] T001 Create project directory structure per plan.md (src/, config/, tests/, scripts/)
- [ ] T002 Initialize Python project with pyproject.toml and requirements.txt
- [ ] T003 [P] Create base YAML config files in config/base.yaml, config/dev.yaml, config/prod.yaml
- [ ] T004 [P] Configure pytest in pyproject.toml with benchmark plugin
- [ ] T005 [P] Configure ruff linter and mypy type checker in pyproject.toml
- [ ] T006 [P] Create .gitignore for models/, logs/, __pycache__, venv/
- [ ] T007 Create scripts/setup.sh for platform-detecting dependency installation
- [ ] T008 Create scripts/download_models.sh for model downloads (whisper, piper)

**Checkpoint**: Project skeleton ready, can install dependencies and run empty tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration System

- [ ] T009 Implement config loader interface in src/config/__init__.py
- [ ] T010 Implement YAML config loading with inheritance in src/config/loader.py
- [ ] T011 Implement profile management (dev/prod) in src/config/profiles.py
- [ ] T012 Write unit tests for config loading in tests/unit/test_config.py

### Audio Abstraction Layer

- [ ] T013 Define AudioCapture protocol in src/audio/capture.py
- [ ] T014 Define AudioPlayback protocol in src/audio/playback.py
- [ ] T015 [P] Implement MockAudioCapture for testing in src/audio/mock_capture.py
- [ ] T016 [P] Implement macOS audio backend in src/audio/platform/macos.py
- [ ] T017 [P] Implement Linux/ALSA audio backend in src/audio/platform/linux.py
- [ ] T018 Create audio module __init__.py with platform auto-detection in src/audio/__init__.py
- [ ] T019 Write unit tests for mock audio capture in tests/unit/test_audio.py

### Feedback System

- [ ] T020 Define FeedbackType enum and AudioFeedback protocol in src/feedback/__init__.py
- [ ] T021 Implement audio feedback (beeps, chimes) in src/feedback/audio.py
- [ ] T022 Add test audio fixtures in tests/fixtures/audio/ (beep.wav, error.wav, etc.)

### Main Entry Point

- [ ] T023 Create package __init__.py in src/__init__.py
- [ ] T024 Create entry point skeleton in src/__main__.py with config loading
- [ ] T025 Verify `python -m ara --help` runs successfully

**Checkpoint**: Foundation ready - audio capture, playback, config, and feedback all functional

---

## Phase 3: User Story 1 - Basic Voice Conversation (Priority: P1) 🎯 MVP

**Goal**: User speaks to Ara and receives a spoken response, all offline

**Independent Test**: Say "Ara, what time is it?" with device in airplane mode, receive accurate spoken response within 6s (Pi) / 1s (laptop)

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T026 [P] [US1] Unit test for WakeWordDetector interface in tests/unit/test_wake_word.py
- [ ] T027 [P] [US1] Unit test for Transcriber interface in tests/unit/test_stt.py
- [ ] T028 [P] [US1] Unit test for LanguageModel interface in tests/unit/test_llm.py
- [ ] T029 [P] [US1] Unit test for Synthesizer interface in tests/unit/test_tts.py
- [ ] T030 [P] [US1] Integration test for voice loop in tests/integration/test_voice_loop.py

### Wake Word Detection

- [ ] T031 [US1] Define WakeWordDetector protocol in src/wake_word/detector.py
- [ ] T032 [US1] Implement Porcupine wake word detector in src/wake_word/porcupine.py
- [ ] T033 [US1] Create wake_word module __init__.py with factory function in src/wake_word/__init__.py

### Speech-to-Text

- [ ] T034 [US1] Define Transcriber protocol and data classes in src/stt/transcriber.py
- [ ] T035 [US1] Implement faster-whisper transcriber in src/stt/whisper.py
- [ ] T036 [US1] Create stt module __init__.py with factory function in src/stt/__init__.py
- [ ] T037 [US1] Add test audio fixture "what_time_is_it.wav" in tests/fixtures/audio/

### Language Model

- [ ] T038 [US1] Define LanguageModel protocol and data classes in src/llm/model.py
- [ ] T039 [US1] Implement Ollama LLM wrapper in src/llm/ollama.py
- [ ] T040 [US1] Create llm module __init__.py with factory function in src/llm/__init__.py
- [ ] T041 [US1] Define voice assistant system prompt in config/base.yaml

### Text-to-Speech

- [ ] T042 [US1] Define Synthesizer protocol and data classes in src/tts/synthesizer.py
- [ ] T043 [US1] Implement Piper TTS synthesizer in src/tts/piper.py
- [ ] T044 [US1] Create tts module __init__.py with factory function in src/tts/__init__.py

### Voice Loop Orchestration

- [ ] T045 [US1] Define Orchestrator class in src/router/orchestrator.py
- [ ] T046 [US1] Implement main voice loop (wake → stt → llm → tts → play) in src/router/orchestrator.py
- [ ] T047 [US1] Wire orchestrator to entry point in src/__main__.py
- [ ] T048 [US1] Add latency logging to each pipeline stage in src/router/orchestrator.py

### Benchmark Tests

- [ ] T049 [P] [US1] Create STT latency benchmark in tests/benchmark/test_stt_latency.py
- [ ] T050 [P] [US1] Create LLM latency benchmark in tests/benchmark/test_llm_latency.py
- [ ] T051 [P] [US1] Create E2E latency benchmark in tests/benchmark/test_e2e_latency.py
- [ ] T052 [US1] Create scripts/benchmark.py runner with P50/P95/P99 reporting

**Checkpoint**: US1 complete - full voice conversation works offline. Can demo "Ara, what's the capital of France?"

---

## Phase 4: User Story 2 - Timers and Reminders (Priority: P2)

**Goal**: User sets timers/reminders via voice, receives alerts when due

**Independent Test**: Say "Ara, set a timer for 1 minute" and verify audio alert plays after 60 seconds

### Tests for User Story 2 ⚠️

- [ ] T053 [P] [US2] Unit test for Timer entity and manager in tests/unit/test_timer.py
- [ ] T054 [P] [US2] Unit test for Reminder entity and manager in tests/unit/test_reminder.py
- [ ] T055 [P] [US2] Unit test for intent classification in tests/unit/test_intent.py
- [ ] T056 [US2] Integration test for timer flow in tests/integration/test_timer_flow.py

### Intent Classification

- [ ] T057 [US2] Define IntentType enum and Intent data class in src/router/intent.py
- [ ] T058 [US2] Implement intent classifier (timer_set, reminder_set, etc.) in src/router/intent.py
- [ ] T059 [US2] Add intent extraction to orchestrator in src/router/orchestrator.py

### Timer Management

- [ ] T060 [US2] Define Timer entity (matching data-model.md) in src/commands/timer.py
- [ ] T061 [US2] Implement TimerManager with create/cancel/query in src/commands/timer.py
- [ ] T062 [US2] Implement timer expiration callback with alert sound in src/commands/timer.py
- [ ] T063 [US2] Add timer_alert.wav audio fixture in tests/fixtures/audio/

### Reminder Management

- [ ] T064 [US2] Define Reminder entity (matching data-model.md) in src/commands/reminder.py
- [ ] T065 [US2] Implement ReminderManager with create/cancel/query in src/commands/reminder.py
- [ ] T066 [US2] Implement reminder scheduler and alert in src/commands/reminder.py
- [ ] T067 [US2] Add reminder_alert.wav audio fixture in tests/fixtures/audio/

### Command Routing

- [ ] T068 [US2] Create commands module __init__.py in src/commands/__init__.py
- [ ] T069 [US2] Integrate timer/reminder handling into orchestrator in src/router/orchestrator.py
- [ ] T070 [US2] Add natural language time parsing (e.g., "5 minutes", "3 PM") in src/commands/timer.py

**Checkpoint**: US2 complete - can set timers and reminders, receive alerts. US1 still works independently.

---

## Phase 5: User Story 3 - Conversation Logging (Priority: P3)

**Goal**: All interactions logged, daily summaries generated automatically

**Independent Test**: Have 5+ interactions, verify daily summary file exists with accurate statistics

### Tests for User Story 3 ⚠️

- [ ] T071 [P] [US3] Unit test for Interaction entity in tests/unit/test_interaction.py
- [ ] T072 [P] [US3] Unit test for storage layer in tests/unit/test_storage.py
- [ ] T073 [P] [US3] Unit test for summary generator in tests/unit/test_summary.py
- [ ] T074 [US3] Integration test for logging flow in tests/integration/test_logging.py

### Storage Layer

- [ ] T075 [US3] Define Interaction entity (matching data-model.md) in src/logger/interaction.py
- [ ] T076 [US3] Define Session entity in src/logger/interaction.py
- [ ] T077 [US3] Implement SQLite storage with WAL mode in src/logger/storage.py
- [ ] T078 [US3] Implement JSONL file writer in src/logger/storage.py
- [ ] T079 [US3] Create database schema (interactions, timers, reminders tables) in src/logger/storage.py

### Interaction Logger

- [ ] T080 [US3] Implement InteractionLogger with log() method in src/logger/interaction.py
- [ ] T081 [US3] Integrate logging into orchestrator (log after each interaction) in src/router/orchestrator.py
- [ ] T082 [US3] Add device_id to all log entries in src/logger/interaction.py

### Daily Summary Generation

- [ ] T083 [US3] Define DailySummary entity (matching data-model.md) in src/logger/summary.py
- [ ] T084 [US3] Implement SummaryGenerator with aggregation logic in src/logger/summary.py
- [ ] T085 [US3] Implement action item extraction from transcripts in src/logger/summary.py
- [ ] T086 [US3] Implement Markdown export for summaries in src/logger/summary.py
- [ ] T087 [US3] Create scripts/daily_summary.py for manual generation

### Query Support

- [ ] T088 [US3] Add "what did I ask yesterday" query handling in src/router/orchestrator.py
- [ ] T089 [US3] Implement log query methods in storage layer in src/logger/storage.py

**Checkpoint**: US3 complete - all interactions logged, summaries generated. US1 and US2 still work.

---

## Phase 6: User Story 4 - On-Demand Internet Features (Priority: P4)

**Goal**: Web search, weather, and cloud LLM when online and explicitly requested

**Independent Test**: Connect to WiFi, say "Ara with internet, search for Raspberry Pi 5", receive web-sourced response

### Tests for User Story 4 ⚠️

- [ ] T090 [P] [US4] Unit test for network detection in tests/unit/test_network.py
- [ ] T091 [P] [US4] Unit test for web search in tests/unit/test_search.py
- [ ] T092 [P] [US4] Unit test for cloud LLM in tests/unit/test_cloud_llm.py
- [ ] T093 [US4] Integration test for online query flow in tests/integration/test_online_flow.py

### Network Detection

- [ ] T094 [US4] Implement network connectivity check in src/router/mode.py
- [ ] T095 [US4] Add periodic connectivity monitoring (30s interval) in src/router/mode.py

### Web Search

- [ ] T096 [US4] Implement DuckDuckGo search wrapper in src/llm/search.py
- [ ] T097 [US4] Add search result summarization via LLM in src/llm/search.py
- [ ] T098 [US4] Add "search for", "with internet" trigger detection in src/router/intent.py

### Cloud LLM (Claude API)

- [ ] T099 [US4] Implement Claude API client in src/llm/cloud.py
- [ ] T100 [US4] Add complexity scoring for query routing in src/router/orchestrator.py
- [ ] T101 [US4] Add cloud fallback for context overflow in src/router/orchestrator.py

### Query Routing

- [ ] T102 [US4] Implement routing logic (local vs cloud) in src/router/orchestrator.py
- [ ] T103 [US4] Add graceful degradation when offline during cloud request in src/router/orchestrator.py
- [ ] T104 [US4] Log response_source (local_llm, cloud_api) in interactions in src/logger/interaction.py

**Checkpoint**: US4 complete - internet features work when online. Offline graceful degradation works.

---

## Phase 7: User Story 5 - Mode Control and Status (Priority: P5)

**Goal**: User can check and switch modes via voice commands

**Independent Test**: Say "Ara, go offline", then "Ara, what mode are you in?" and hear "offline"

### Tests for User Story 5 ⚠️

- [ ] T105 [P] [US5] Unit test for ModeManager in tests/unit/test_mode.py
- [ ] T106 [US5] Integration test for mode switching in tests/integration/test_mode_switch.py

### Mode Manager

- [ ] T107 [US5] Define OperationMode enum in src/router/mode.py
- [ ] T108 [US5] Implement ModeManager with get/set mode in src/router/mode.py
- [ ] T109 [US5] Persist mode preference to UserPreference in src/router/mode.py

### System Commands

- [ ] T110 [US5] Implement system command handlers in src/commands/system.py
- [ ] T111 [US5] Add "go offline", "go online", "what mode" intent types in src/router/intent.py
- [ ] T112 [US5] Integrate system commands into orchestrator in src/router/orchestrator.py
- [ ] T113 [US5] Add mode change audio feedback (chimes) in src/feedback/audio.py

### Status Reporting

- [ ] T114 [US5] Implement status query response generation in src/commands/system.py
- [ ] T115 [US5] Add offline/online indicator to startup message in src/__main__.py

**Checkpoint**: US5 complete - mode control works. All previous stories still functional.

---

## Phase 8: User Story 6 - Cross-Platform Development (Priority: P6)

**Goal**: Identical behavior on laptop and Pi 4, mock audio for CI, automated tests

**Independent Test**: Run same test suite on laptop and Pi 4, verify identical behavior for same inputs

### Tests for User Story 6 ⚠️

- [ ] T116 [P] [US6] Platform parity test in tests/integration/test_platform_parity.py
- [ ] T117 [P] [US6] CI pipeline test with mock audio in tests/integration/test_ci_mock.py

### Platform Detection

- [ ] T118 [US6] Implement platform detection utility in src/config/profiles.py
- [ ] T119 [US6] Add GPU acceleration detection (Metal/CUDA/CPU) in src/config/profiles.py

### Mock Audio Enhancement

- [ ] T120 [US6] Enhance MockAudioCapture to load WAV files by name in src/audio/mock_capture.py
- [ ] T121 [US6] Add --mock-audio CLI flag to entry point in src/__main__.py
- [ ] T122 [US6] Add --test-utterance CLI flag for specific test file in src/__main__.py

### CI/CD Pipeline

- [ ] T123 [US6] Create GitHub Actions workflow in .github/workflows/ci.yml
- [ ] T124 [US6] Configure CI to run tests with mock audio
- [ ] T125 [US6] Add platform matrix (ubuntu, macos) to CI workflow

### Test Fixtures

- [ ] T126 [P] [US6] Add additional test WAV fixtures in tests/fixtures/audio/
- [ ] T127 [US6] Create test fixture manifest in tests/fixtures/audio/manifest.json
- [ ] T128 [US6] Document fixture creation process in tests/fixtures/audio/README.md

**Checkpoint**: US6 complete - CI passes on both platforms. Full cross-platform development enabled.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, optimization, and final quality improvements

### Documentation

- [ ] T129 [P] Update README.md with installation and usage instructions
- [ ] T130 [P] Update ara-voice-assistant-pi4-setup.md with latest setup steps
- [ ] T131 [P] Add inline docstrings to all public interfaces
- [ ] T132 Verify quickstart.md accuracy by following steps on fresh machine

### Performance Optimization

- [ ] T133 Profile and optimize STT latency on Pi 4
- [ ] T134 Profile and optimize LLM latency on Pi 4
- [ ] T135 Implement model preloading for faster first response in src/__main__.py
- [ ] T136 Run full benchmark suite and document results in BENCHMARKS.md

### Error Handling

- [ ] T137 Implement ModuleError standard across all modules
- [ ] T138 Add user-friendly error messages for all failure modes
- [ ] T139 Add retry logic for transient failures in src/router/orchestrator.py

### Security

- [ ] T140 Ensure API keys use environment variables, not config files
- [ ] T141 Verify no raw audio is stored by default
- [ ] T142 Add optional log encryption at rest in src/logger/storage.py

### Final Validation

- [ ] T143 Run full test suite on Pi 4 hardware
- [ ] T144 Run 24-hour stability test on Pi 4
- [ ] T145 Validate all Constitution principles are met (constitution checklist)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS all user stories)
    ↓
┌───────────────────────────────────────────────────────────┐
│ Phase 3-8: User Stories (can run in parallel or sequence) │
│   US1 (P1) → US2 (P2) → US3 (P3) → US4 (P4) → US5 (P5) → US6 (P6)   │
└───────────────────────────────────────────────────────────┘
    ↓
Phase 9: Polish (after desired stories complete)
```

### User Story Dependencies

| Story | Depends On | Can Start After |
|-------|------------|-----------------|
| US1 (Basic Voice) | Foundational | Phase 2 complete |
| US2 (Timers) | US1 (needs voice loop) | Phase 3 complete |
| US3 (Logging) | US1 (needs interactions) | Phase 3 complete |
| US4 (Internet) | US1 (needs voice loop) | Phase 3 complete |
| US5 (Mode Control) | US4 (needs mode concept) | Phase 6 complete |
| US6 (Cross-Platform) | All stories (tests all) | Phase 7 complete |

### Within Each User Story

1. Tests written FIRST (must FAIL)
2. Interfaces/protocols before implementations
3. Core logic before integrations
4. Integration last
5. Checkpoint validation

---

## Parallel Opportunities

### Phase 2 (Foundational)

```bash
# Launch in parallel:
T016 "Implement macOS audio backend in src/audio/platform/macos.py"
T017 "Implement Linux/ALSA audio backend in src/audio/platform/linux.py"
```

### Phase 3 (US1 Tests)

```bash
# Launch in parallel:
T026 "Unit test for WakeWordDetector"
T027 "Unit test for Transcriber"
T028 "Unit test for LanguageModel"
T029 "Unit test for Synthesizer"
```

### Phase 3 (US1 Benchmarks)

```bash
# Launch in parallel:
T049 "STT latency benchmark"
T050 "LLM latency benchmark"
T051 "E2E latency benchmark"
```

### Phase 4 (US2 Tests)

```bash
# Launch in parallel:
T053 "Unit test for Timer"
T054 "Unit test for Reminder"
T055 "Unit test for intent classification"
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup ✓
2. Complete Phase 2: Foundational ✓
3. Complete Phase 3: User Story 1 (Basic Voice)
4. **STOP and VALIDATE**: Test US1 independently
5. Deploy/demo: "Ara, what's the capital of France?"

### Incremental Delivery

| Milestone | Stories | Demo |
|-----------|---------|------|
| MVP | US1 | Voice Q&A works offline |
| v0.2 | US1 + US2 | Timers and reminders work |
| v0.3 | US1-3 | Conversation logging, daily summaries |
| v0.4 | US1-4 | Web search, cloud features |
| v0.5 | US1-5 | Mode control, user preferences |
| v1.0 | US1-6 | Full cross-platform, CI/CD |

### Suggested MVP Scope

**US1 only** - Basic Voice Conversation

This delivers the core value proposition:
- Wake word detection
- Speech-to-text
- Local LLM response
- Text-to-speech output
- Full offline operation

Can be completed and demoed independently before adding other features.

---

## Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Phase 1: Setup | 8 | 4 |
| Phase 2: Foundational | 17 | 4 |
| Phase 3: US1 (MVP) | 27 | 9 |
| Phase 4: US2 | 18 | 4 |
| Phase 5: US3 | 19 | 4 |
| Phase 6: US4 | 15 | 4 |
| Phase 7: US5 | 11 | 2 |
| Phase 8: US6 | 13 | 3 |
| Phase 9: Polish | 17 | 3 |
| **Total** | **145** | **37** |

**Task Count by User Story**:
- US1: 27 tasks (MVP)
- US2: 18 tasks
- US3: 19 tasks
- US4: 15 tasks
- US5: 11 tasks
- US6: 13 tasks
- Setup/Foundation/Polish: 42 tasks
