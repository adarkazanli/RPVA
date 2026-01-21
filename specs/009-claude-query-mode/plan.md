# Implementation Plan: Claude Query Mode

**Branch**: `009-claude-query-mode` | **Date**: 2026-01-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-claude-query-mode/spec.md`

## Summary

Add a special "ask Claude" voice command mode that routes user queries to the Claude API (using Claude Max subscription), maintains conversation context for follow-up questions, provides audio feedback while waiting, and logs all queries/responses to MongoDB for later summarization by time period.

**Key Technical Approach**:
- Extend existing `IntentClassifier` with new `CLAUDE_QUERY` intent type
- Leverage existing `CloudLanguageModel` for Claude API integration (already uses Anthropic SDK)
- Use existing `FeedbackType` system for waiting indicator (musical loop)
- Extend MongoDB storage with new `claude_queries` collection
- Implement session management for conversation history persistence

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: anthropic (existing), pymongo (existing), sounddevice (existing), faster-whisper (existing), piper (existing)
**Storage**: MongoDB (local Docker container, existing infrastructure)
**Testing**: pytest (existing)
**Target Platform**: Raspberry Pi 4 (8GB RAM), Raspberry Pi OS (64-bit) Lite
**Project Type**: Single project (existing Ara voice assistant)
**Performance Goals**:
- Response within 10 seconds for typical queries (SC-001)
- Audio indicator within 500ms of query submission (SC-007)
- Connectivity check within 2 seconds (SC-008)
**Constraints**:
- Total memory usage under 6GB (existing constraint)
- Claude API calls require internet connectivity
- 30-second timeout for Claude responses (FR-013)
**Scale/Scope**: Single user, personal assistant use case

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | ✅ PASS | Claude queries are inherently slower (network-bound); defined timeout (30s) and feedback (500ms indicator) meet user expectations |
| II. Offline-First | ⚠️ JUSTIFIED | Claude query feature explicitly requires internet; gracefully degrades with connectivity check (FR-011) and clear error messages (FR-007) |
| III. Modularity | ✅ PASS | New `claude/` module with clear interface; integrates with existing router, storage, feedback modules |
| IV. Simplicity (YAGNI) | ✅ PASS | Leverages existing CloudLanguageModel, IntentClassifier, and MongoDB patterns |
| V. Test-Driven Development | ✅ PASS | Tests required for intent recognition, session management, storage operations |
| VI. Benchmark-Driven Optimization | ✅ PASS | No performance-critical paths beyond existing latency targets |
| VII. Documentation-First | ✅ PASS | Voice command reference will be updated |

**Principle II Justification**: The Claude query feature is an explicitly user-triggered internet feature (using "ask Claude" trigger phrase), consistent with the Constitution's allowance for "explicitly user-triggered features (e.g., 'Ara with internet, search for...')". The core voice assistant remains fully functional offline.

## Project Structure

### Documentation (this feature)

```text
specs/009-claude-query-mode/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/ara/
├── claude/                    # NEW: Claude query module
│   ├── __init__.py
│   ├── client.py              # Claude API client wrapper (extends CloudLanguageModel)
│   ├── session.py             # Conversation session management
│   └── handler.py             # Intent handler for Claude queries
├── router/
│   └── intent.py              # MODIFY: Add CLAUDE_QUERY, CLAUDE_SUMMARY, CLAUDE_RESET intents
├── storage/
│   └── claude_repository.py   # NEW: MongoDB repository for Claude queries
├── feedback/
│   └── __init__.py            # MODIFY: Add CLAUDE_WAITING feedback type
└── config/
    └── __init__.py            # MODIFY: Add Claude configuration

tests/
├── unit/
│   ├── test_claude_client.py       # NEW
│   ├── test_claude_session.py      # NEW
│   └── test_claude_intent.py       # NEW
├── integration/
│   └── test_claude_flow.py         # NEW: End-to-end Claude query flow
└── contract/
    └── test_claude_storage.py      # NEW: MongoDB contract tests
```

**Structure Decision**: Single project structure following existing Ara patterns. New `claude/` module encapsulates Claude-specific functionality while integrating with existing router, storage, and feedback systems.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Internet dependency | Claude API requires network | This is an explicitly user-triggered feature; offline alternatives (local Ollama) already exist for core functionality |
