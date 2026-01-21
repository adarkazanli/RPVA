# Implementation Plan: Platform-Adaptive Text-to-Speech

**Branch**: `010-platform-tts` | **Date**: 2026-01-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/010-platform-tts/spec.md`

## Summary

Implement automatic platform detection to select the optimal TTS engine at runtime: macOS native TTS (using "Samantha" voice) on Mac, Piper TTS on Raspberry Pi. The system will maintain the existing `Synthesizer` protocol interface, provide a fallback chain for reliability, and require zero user configuration.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing ara.tts module, subprocess (for macOS `say` command)
**Storage**: N/A (no persistence needed)
**Testing**: pytest
**Target Platform**: macOS (development), Raspberry Pi 4 (production)
**Project Type**: Single project (existing codebase extension)
**Performance Goals**: TTS response within 500ms per constitution (0.5s TTS budget)
**Constraints**: Must maintain existing `Synthesizer` protocol; no new cloud dependencies
**Scale/Scope**: 2 new TTS implementations (macOS, fallback), 1 platform detector

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | ✅ PASS | TTS budget is 0.5s; both macOS native and Piper meet this |
| II. Offline-First | ✅ PASS | Both TTS engines are fully local; no cloud dependencies |
| III. Modularity | ✅ PASS | New synthesizers implement existing `Synthesizer` protocol |
| IV. Simplicity (YAGNI) | ✅ PASS | Minimal implementation - just platform detection + 1 new synthesizer |
| V. Test-Driven Development | ✅ WILL COMPLY | Tests will be written for platform detection and macOS synthesizer |
| VI. Benchmark-Driven | ✅ WILL COMPLY | Latency benchmarks for both platforms |
| VII. Documentation-First | ✅ WILL COMPLY | Update voice-commands.md if needed |

**Gate Status**: ✅ PASSED - No violations; proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-platform-tts/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
src/ara/tts/
├── __init__.py          # Update create_synthesizer() with platform detection
├── synthesizer.py       # Existing Synthesizer protocol (no changes)
├── piper.py             # Existing PiperSynthesizer (no changes)
├── mock.py              # Existing MockSynthesizer (no changes)
├── macos.py             # NEW: MacOSSynthesizer implementation
└── platform.py          # NEW: Platform detection utility

tests/
├── unit/
│   ├── test_tts.py              # Existing tests
│   ├── test_macos_synthesizer.py # NEW: macOS TTS tests
│   └── test_platform_detection.py # NEW: Platform detection tests
└── integration/
    └── test_platform_tts.py      # NEW: End-to-end platform TTS tests
```

**Structure Decision**: Extends existing `src/ara/tts/` module with new files for macOS synthesizer and platform detection. No structural changes to repository layout.

## Complexity Tracking

> No violations - table not needed.
