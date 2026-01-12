<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version change: N/A → 1.0.0 (Initial ratification)

Modified principles: N/A (initial version)

Added sections:
- Core Principles (7 principles)
- Technology Stack
- Development Workflow
- Governance

Removed sections: N/A (initial version)

Templates requiring updates:
- .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section exists)
- .specify/templates/spec-template.md: ✅ Compatible (Requirements/Success Criteria align)
- .specify/templates/tasks-template.md: ✅ Compatible (TDD workflow, parallel task markers)

Follow-up TODOs: None
================================================================================
-->

# RPVA (Raspberry Pi Voice Assistant) Constitution

## Core Principles

### I. Performance-First

All components MUST meet defined latency targets. End-to-end response time for local queries MUST be under 6 seconds. Individual component budgets:

| Component | Maximum Latency |
|-----------|-----------------|
| STT (Speech-to-Text) | 1.5 seconds |
| LLM (Response Generation) | 4 seconds |
| TTS (Text-to-Speech) | 0.5 seconds |

**Rationale**: Voice assistants require near-real-time interaction to feel natural. Exceeding these targets degrades user experience unacceptably.

**Enforcement**: Every PR affecting STT, LLM, or TTS components MUST include benchmark results demonstrating compliance with latency targets.

### II. Offline-First

The core voice assistant MUST function fully without internet connectivity. All primary features (wake word detection, speech recognition, response generation, speech synthesis) MUST use local models only.

Internet access is permitted ONLY for explicitly user-triggered features (e.g., "Ara with internet, search for...").

**Rationale**: Privacy, reliability, and independence from external services are foundational to the project's value proposition.

**Enforcement**: No cloud API dependencies in the core pipeline. Internet-dependent features MUST gracefully degrade when offline.

### III. Modularity

The system MUST maintain clear separation between components:

- **STT Module**: Speech-to-text (faster-whisper)
- **LLM Module**: Response generation (Ollama/Gemma)
- **TTS Module**: Text-to-speech (Piper)
- **Search Module**: Optional internet access (DuckDuckGo)
- **Audio Module**: Recording/playback

Each module MUST be independently testable and replaceable without affecting other components.

**Rationale**: Enables component upgrades (e.g., swapping STT models), isolated testing, and clearer debugging.

**Enforcement**: Modules communicate through defined interfaces only. No direct cross-module dependencies.

### IV. Simplicity (YAGNI)

Implementation MUST use the minimum complexity required. Do not add:

- Features not explicitly specified
- Abstractions for hypothetical future requirements
- Configuration options beyond current needs
- Cloud fallbacks for local-only features

**Rationale**: Raspberry Pi has constrained resources. Every unnecessary abstraction costs memory, CPU cycles, and maintenance burden.

**Enforcement**: Code review MUST challenge any complexity not directly tied to a current requirement.

### V. Test-Driven Development

For non-trivial changes, the development sequence MUST be:

1. Write test(s) defining expected behavior
2. Verify test(s) fail (Red)
3. Implement minimum code to pass (Green)
4. Refactor while maintaining passing tests

Test categories:
- **Unit tests**: Individual functions/methods
- **Integration tests**: Module interactions
- **Benchmark tests**: Performance validation

**Rationale**: TDD prevents regression, documents behavior, and ensures testable design.

**Enforcement**: PRs for feature work MUST include corresponding tests. Test-to-code commit ordering tracked.

### VI. Benchmark-Driven Optimization

Performance changes MUST be validated by benchmarks, not assumptions. The benchmark suite (`benchmark.py`) MUST:

- Measure each component independently
- Report latency percentiles (p50, p95, p99)
- Compare against defined targets
- Run on target hardware (Raspberry Pi 4)

**Rationale**: Perceived performance improvements without measurement often introduce regressions or optimize the wrong bottleneck.

**Enforcement**: Performance-related PRs MUST include before/after benchmark results from Raspberry Pi 4 hardware.

### VII. Documentation-First

User-facing changes MUST update documentation before or alongside code changes:

- Setup guide (`ara-voice-assistant-pi4-setup.md`)
- Voice command reference
- Troubleshooting section
- Configuration options

Internal changes SHOULD include inline comments only where logic is non-obvious.

**Rationale**: Documentation enables reproducibility and reduces support burden. The setup guide is the primary deliverable.

**Enforcement**: PRs adding user-facing features MUST include documentation updates. Reviewers verify documentation accuracy.

## Technology Stack

**Target Platform**: Raspberry Pi 4 (8GB RAM), Raspberry Pi OS (64-bit) Lite

| Layer | Technology | Justification |
|-------|------------|---------------|
| Language | Python 3.11+ | Ecosystem support for ML/audio |
| STT | faster-whisper (small, int8) | Best accuracy/speed tradeoff for ARM |
| LLM | Ollama + Gemma 2 2B (Q4_K_M) | Fits in memory, reasonable latency |
| TTS | Piper (medium voice) | Optimized for Pi, natural output |
| Search | duckduckgo-search | No API key, privacy-respecting |
| Audio | sounddevice, ALSA | Low-level control, minimal overhead |

**Constraints**:
- Total memory usage MUST stay under 6GB (leaving headroom for OS)
- Swap usage during normal operation SHOULD be minimal
- CPU governor SHOULD be set to "performance" during operation

## Development Workflow

### Change Process

1. **Specification**: Define what, not how (user stories, acceptance criteria)
2. **Planning**: Technical approach, component impacts, latency budget
3. **Test Writing**: Tests first, verify failure
4. **Implementation**: Minimum viable solution
5. **Benchmarking**: Validate performance on target hardware
6. **Documentation**: Update guides and references
7. **Review**: Constitution compliance check

### Commit Standards

- Atomic commits (one logical change per commit)
- Message format: `<type>: <description>` (types: feat, fix, perf, docs, test, refactor)
- Include benchmark results in perf commits

### Branch Strategy

- `master`: Stable, tested, documented
- `feature/*`: New capabilities
- `fix/*`: Bug corrections
- `perf/*`: Performance improvements

## Governance

### Constitution Authority

This constitution supersedes all other development practices. Deviations MUST be:

1. Documented in PR description
2. Justified with specific reasoning
3. Approved by project maintainer
4. Tracked in Complexity Tracking table (see plan-template.md)

### Amendment Process

1. Propose amendment with rationale
2. Assess impact on existing code and templates
3. Update version number per semantic versioning:
   - MAJOR: Principle removal or redefinition
   - MINOR: New principle or significant expansion
   - PATCH: Clarifications, typos, refinements
4. Propagate changes to dependent templates
5. Document in Sync Impact Report

### Compliance Review

All PRs MUST pass Constitution Check before merge:

- [ ] Latency targets met (Principle I)
- [ ] No new cloud dependencies in core (Principle II)
- [ ] Module boundaries respected (Principle III)
- [ ] No unnecessary complexity (Principle IV)
- [ ] Tests included for features (Principle V)
- [ ] Benchmarks for performance changes (Principle VI)
- [ ] Documentation updated (Principle VII)

**Version**: 1.0.0 | **Ratified**: 2026-01-12 | **Last Amended**: 2026-01-12
