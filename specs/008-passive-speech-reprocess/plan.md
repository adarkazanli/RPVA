# Implementation Plan: Passive Speech Interrupt and Reprocessing

**Branch**: `008-passive-speech-reprocess` | **Date**: 2026-01-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-passive-speech-reprocess/spec.md`

## Summary

Enable the voice assistant to detect user speech during response delivery, immediately stop playback, accumulate all user input (original + interrupts), and reprocess the combined input to determine actual intent. Includes a 5-second continuation window after response completion. Implementation requires modifications to the orchestrator's recording loop, playback interruption capability, and a new request buffer management system.

## Technical Context

**Language/Version**: Python 3.11+ (existing codebase)
**Primary Dependencies**: sounddevice (audio), faster-whisper (STT), piper (TTS), ollama (LLM) - all existing
**Storage**: In-memory request buffer (no persistent storage needed)
**Testing**: pytest (existing)
**Target Platform**: Raspberry Pi 4 (8GB RAM), Raspberry Pi OS 64-bit Lite
**Project Type**: Single project (existing structure)
**Performance Goals**:
- TTS stop within 500ms of user speech (SC-001)
- Reprocessing complete within 2 seconds of silence end (SC-002)
- Constitution: End-to-end response under 6 seconds
**Constraints**:
- Total memory under 6GB
- Must work offline (no cloud VAD)
- Must not interfere with existing wake word detection
**Scale/Scope**: Single user, single conversation turn with unlimited interrupts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | ✅ PASS | 500ms TTS stop + 2s reprocess within 6s budget. Component budgets: STT 1.5s, LLM 4s, TTS 0.5s still apply. |
| II. Offline-First | ✅ PASS | No cloud dependencies. Energy-based VAD is local. |
| III. Modularity | ✅ PASS | Changes scoped to orchestrator + audio modules. Clean protocol boundaries maintained. |
| IV. Simplicity (YAGNI) | ✅ PASS | Minimal additions: interrupt flag, request buffer, continuation timer. No unnecessary abstractions. |
| V. Test-Driven Development | ✅ PASS | Unit tests for buffer, integration tests for interrupt flow. Tests written first. |
| VI. Benchmark-Driven Optimization | ✅ PASS | Will benchmark TTS stop latency and reprocess time on Pi 4. |
| VII. Documentation-First | ✅ PASS | Will update voice command reference with interrupt behavior. |

**Gate Result**: PASS - No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/008-passive-speech-reprocess/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal Python protocols)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── ara/
│   ├── __main__.py              # Entry point (no changes)
│   ├── router/
│   │   ├── orchestrator.py      # MODIFY: Add interrupt detection, request buffer, continuation window
│   │   ├── intent.py            # No changes (reprocessing uses existing classify())
│   │   └── interrupt.py         # NEW: Interrupt state machine and buffer management
│   ├── audio/
│   │   ├── playback.py          # MODIFY: Add interrupt() method to protocol
│   │   └── backends/
│   │       ├── macos.py         # MODIFY: Implement interrupt()
│   │       └── linux.py         # MODIFY: Implement interrupt()
│   ├── feedback/
│   │   └── audio.py             # MODIFY: Add interrupt acknowledgment sound
│   └── [other modules unchanged]

tests/
├── unit/
│   ├── test_interrupt.py        # NEW: Request buffer, continuation window tests
│   └── test_playback.py         # MODIFY: Add interrupt tests
├── integration/
│   └── test_interrupt_flow.py   # NEW: End-to-end interrupt scenarios
└── [other tests unchanged]
```

**Structure Decision**: Single project structure maintained. New `interrupt.py` module added to `router/` to encapsulate interrupt state management while keeping `orchestrator.py` focused on coordination.

## Complexity Tracking

> No violations requiring justification. All changes follow existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
