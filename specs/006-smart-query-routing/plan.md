# Implementation Plan: Smarter Query Routing

**Branch**: `006-smart-query-routing` | **Date**: 2026-01-14 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-smart-query-routing/spec.md`

## Summary

Implement intelligent query routing to ensure queries are answered by the most appropriate data source (MongoDB for personal data, Tavily for factual/current info, LLM for general knowledge). This prevents LLM hallucination of personal data and factual information by routing queries to authoritative sources first.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Existing codebase (ara.router, ara.storage, ara.search)
**Storage**: MongoDB (existing) for personal data queries
**Testing**: pytest (existing test infrastructure)
**Target Platform**: Raspberry Pi 4 (8GB RAM), also macOS for development
**Project Type**: Single project (voice assistant)
**Performance Goals**: Query classification adds <100ms latency
**Constraints**: Must work offline for DB queries, graceful degradation when services unavailable
**Scale/Scope**: Single user, ~100 interactions/day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | PASS | Classification adds <100ms, within budget |
| II. Offline-First | PASS | DB queries work offline, web search degrades gracefully |
| III. Modularity | PASS | QueryRouter is a new module with defined interface |
| IV. Simplicity (YAGNI) | PASS | Minimal complexity - pattern matching + routing table |
| V. Test-Driven Development | PASS | Tests will be written first |
| VI. Benchmark-Driven Optimization | N/A | No performance optimization, just routing logic |
| VII. Documentation-First | PASS | Will document query routing behavior |

## Project Structure

### Documentation (this feature)

```text
specs/006-smart-query-routing/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/ara/
├── router/
│   ├── __init__.py
│   ├── intent.py          # MODIFY: Add query type indicators
│   ├── orchestrator.py    # MODIFY: Integrate QueryRouter
│   └── query_router.py    # NEW: Smart routing logic
├── storage/
│   └── queries.py         # MODIFY: Add "not found" responses
└── search/
    └── tavily.py          # Existing (no changes)

tests/
├── unit/
│   ├── test_query_router.py   # NEW: Unit tests for routing
│   └── test_intent.py         # MODIFY: Add routing tests
└── integration/
    └── test_routing_flow.py   # NEW: End-to-end routing tests
```

**Structure Decision**: Extends existing single-project structure. New `query_router.py` module handles routing decisions, integrated into existing `orchestrator.py` flow.

## Complexity Tracking

> No constitution violations - keeping implementation simple with pattern matching.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
