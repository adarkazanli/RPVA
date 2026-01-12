# Implementation Plan: Ara Voice Assistant

**Branch**: `001-ara-voice-assistant` | **Date**: 2026-01-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-ara-voice-assistant/spec.md`

## Summary

Ara is a privacy-first, offline-capable voice assistant for Raspberry Pi 4 and development laptops. The system provides low-latency voice interactions using local models for wake word detection, speech-to-text, language model inference, and text-to-speech. It supports on-demand internet features, conversation logging with daily summaries, and cross-platform development with identical behavior on Pi 4 and macOS/Linux.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- Wake Word: Porcupine or OpenWakeWord
- STT: Whisper.cpp (via faster-whisper Python bindings)
- LLM: llama.cpp (via Ollama) with Llama 3.2 3B Q4_K_M
- TTS: Piper TTS
- Audio: PyAudio, sounddevice
- Search: duckduckgo-search
- Config: PyYAML
- Testing: pytest, pytest-benchmark

**Storage**: SQLite (interaction logs) + JSON Lines files (daily logs) + Markdown (summaries)
**Testing**: pytest with fixtures, benchmark tests, mock audio system
**Target Platform**:
- Production: Raspberry Pi 4 (8GB), Raspberry Pi OS 64-bit Lite
- Development: macOS 12+ / Ubuntu 22.04+, x86_64 or ARM64

**Project Type**: Single project with platform abstraction layer
**Performance Goals**:
- Pi 4: <2s P95 end-to-end response, <30s cold boot
- Laptop: <1s P95 end-to-end response, <10s cold boot

**Constraints**:
- Memory: <6GB active on Pi 4, <8GB on laptop
- Offline: Core features must work without internet
- Latency budget: Wake <200ms, STT <1000ms, LLM <1500ms, TTS <500ms

**Scale/Scope**: Single user, 20+ daily interactions, 90-day log retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Performance-First | ✅ PASS | Latency budgets defined per component; benchmark tests required |
| II. Offline-First | ✅ PASS | All core features use local models; internet opt-in only |
| III. Modularity | ✅ PASS | Separate modules: audio, wake_word, stt, llm, tts, router, logger |
| IV. Simplicity (YAGNI) | ✅ PASS | MVP scope defined; extended features deferred to post-MVP |
| V. Test-Driven Development | ✅ PASS | pytest with unit/integration/benchmark; mock audio for CI |
| VI. Benchmark-Driven | ✅ PASS | benchmark.py required; P50/P95/P99 reporting |
| VII. Documentation-First | ✅ PASS | quickstart.md, setup guide updates required |

**Gate Status**: PASSED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-ara-voice-assistant/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Technology decisions
├── data-model.md        # Phase 1: Entity definitions
├── quickstart.md        # Phase 1: Developer setup guide
├── contracts/           # Phase 1: API contracts
│   └── internal-api.md  # Internal module interfaces
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
src/
├── __init__.py
├── __main__.py              # Entry point: python -m ara
├── config/
│   ├── __init__.py
│   ├── loader.py            # YAML config loading
│   └── profiles.py          # Dev/prod profile management
├── audio/
│   ├── __init__.py
│   ├── capture.py           # AudioCapture interface
│   ├── playback.py          # AudioPlayback interface
│   ├── mock_capture.py      # Mock for testing
│   └── platform/
│       ├── macos.py         # CoreAudio implementation
│       └── linux.py         # ALSA implementation
├── wake_word/
│   ├── __init__.py
│   ├── detector.py          # WakeWordDetector interface
│   └── porcupine.py         # Porcupine implementation
├── stt/
│   ├── __init__.py
│   ├── transcriber.py       # Transcriber interface
│   └── whisper.py           # Whisper.cpp implementation
├── llm/
│   ├── __init__.py
│   ├── model.py             # LanguageModel interface
│   ├── ollama.py            # Ollama/llama.cpp implementation
│   └── cloud.py             # Claude API (optional)
├── tts/
│   ├── __init__.py
│   ├── synthesizer.py       # Synthesizer interface
│   └── piper.py             # Piper implementation
├── router/
│   ├── __init__.py
│   ├── intent.py            # Intent classification
│   ├── mode.py              # Online/offline mode management
│   └── orchestrator.py      # Request routing logic
├── commands/
│   ├── __init__.py
│   ├── timer.py             # Timer management
│   ├── reminder.py          # Reminder management
│   └── system.py            # System commands (mode, status)
├── logger/
│   ├── __init__.py
│   ├── interaction.py       # Interaction logging
│   ├── summary.py           # Daily summary generation
│   └── storage.py           # SQLite + JSONL persistence
└── feedback/
    ├── __init__.py
    └── audio.py             # Beeps, chimes, error tones

config/
├── base.yaml                # Shared configuration
├── dev.yaml                 # Laptop overrides
└── prod.yaml                # Pi 4 overrides

models/                      # Downloaded models (gitignored)
├── whisper/
├── llama/
└── piper/

logs/                        # Interaction logs (gitignored)
summaries/                   # Daily summaries

tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── fixtures/
│   └── audio/               # Test WAV files
├── unit/
│   ├── test_config.py
│   ├── test_timer.py
│   ├── test_reminder.py
│   └── test_intent.py
├── integration/
│   ├── test_voice_loop.py
│   ├── test_logging.py
│   └── test_mode_switch.py
└── benchmark/
    ├── test_stt_latency.py
    ├── test_llm_latency.py
    └── test_e2e_latency.py

scripts/
├── setup.sh                 # Platform-detecting setup
├── download_models.sh       # Model downloader
├── benchmark.py             # Benchmark runner
└── daily_summary.py         # Manual summary trigger
```

**Structure Decision**: Single project structure with platform abstraction layer in `src/audio/platform/`. This maintains simplicity while enabling cross-platform development. No separate frontend/backend needed as this is a CLI/voice application.

## Complexity Tracking

> No constitution violations requiring justification. Design follows all 7 principles.

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Platform abstraction | Interface + implementations | Required by spec FR-023; minimal overhead |
| Config profiles | YAML inheritance | Standard pattern; keeps prod/dev separation clean |
| Dual storage (SQLite + JSONL) | SQLite for queries, JSONL for portability | Matches PRD requirements; both are simple |
