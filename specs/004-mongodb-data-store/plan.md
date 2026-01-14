# Implementation Plan: MongoDB Data Store for Voice Agent

**Branch**: `004-mongodb-data-store` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-mongodb-data-store/spec.md`

## Summary

Deploy a local MongoDB instance in Docker to provide persistent storage for voice agent interactions. Enable time-based queries (duration between events, activities around a time point) and natural language event extraction. The system will migrate from existing SQLite storage to MongoDB for improved document-based querying capabilities while maintaining offline-first operation through local containerized deployment.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pymongo (MongoDB driver), motor (async driver), Docker
**Storage**: MongoDB 7.0+ (local Docker container)
**Testing**: pytest, pytest-asyncio
**Target Platform**: Raspberry Pi 4 (8GB RAM), macOS/Linux development
**Project Type**: single
**Performance Goals**: Query response <2s for time-based queries (per SC-001, SC-002)
**Constraints**: <6GB total memory (Constitution), offline-capable, local-only deployment
**Scale/Scope**: 30+ days historical data (SC-005), single user, auto-archive for older data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | ✅ PASS | Query targets <2s align with 6s total latency budget. MongoDB queries don't affect STT/LLM/TTS pipeline latency. |
| II. Offline-First | ✅ PASS | MongoDB runs locally in Docker container. No cloud dependencies. |
| III. Modularity | ✅ PASS | New `storage` module with defined interfaces. Existing `logger` module will use storage abstraction. |
| IV. Simplicity (YAGNI) | ✅ PASS | Implements only specified requirements (time queries, event extraction, persistence). No premature optimization. |
| V. Test-Driven Development | ⏳ PENDING | Tests will be written before implementation per TDD workflow. |
| VI. Benchmark-Driven | ⏳ PENDING | Query performance benchmarks required before merge. |
| VII. Documentation-First | ⏳ PENDING | User documentation for time queries will accompany implementation. |

## Project Structure

### Documentation (this feature)

```text
specs/004-mongodb-data-store/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal Python interfaces)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/ara/
├── storage/              # NEW: MongoDB storage module
│   ├── __init__.py
│   ├── client.py         # MongoDB connection management
│   ├── events.py         # Event extraction and storage
│   ├── queries.py        # Time-based query handlers
│   └── models.py         # Document models (Interaction, Event, Activity)
├── router/
│   ├── intent.py         # MODIFY: Add TIME_QUERY, EVENT_LOG intent types
│   └── orchestrator.py   # MODIFY: Route time queries to storage module
├── logger/
│   ├── storage.py        # MODIFY: Add MongoDB backend option
│   └── interaction.py    # EXISTING: No changes needed
└── commands/
    └── time_query.py     # NEW: Time query command handlers

tests/
├── unit/
│   ├── test_storage_client.py
│   ├── test_event_extraction.py
│   └── test_time_queries.py
├── integration/
│   └── test_mongodb_integration.py
└── benchmark/
    └── test_query_latency.py

docker/
└── docker-compose.yml    # NEW: MongoDB container configuration
```

**Structure Decision**: Single project structure. New `storage` module follows existing modular pattern (similar to `logger`, `llm`, `tts` modules). MongoDB container configuration in `docker/` directory.

## Complexity Tracking

> No constitution violations identified. All principles pass.
