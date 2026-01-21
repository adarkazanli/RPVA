# Implementation Plan: Email Action Items

**Branch**: `007-email-action-items` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-email-action-items/spec.md`

## Summary

Enable users to email their action items via voice command. The system will send a plain text email containing a formatted list of action items (for today or yesterday) to the configured EMAIL_ADDRESS using SMTP with user-provided credentials.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: smtplib (stdlib), email.mime (stdlib), existing Ara orchestrator
**Storage**: N/A (reads from existing MongoDB notes collection)
**Testing**: pytest
**Target Platform**: Raspberry Pi 4 (8GB RAM), Raspberry Pi OS (64-bit) Lite
**Project Type**: single
**Performance Goals**: Email sent within 30 seconds of voice command
**Constraints**: Offline-first for query, online required for SMTP send; graceful degradation if SMTP unavailable
**Scale/Scope**: Single user, personal assistant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | ✅ PASS | Email send is async/background; doesn't block voice response pipeline. LLM not involved. |
| II. Offline-First | ✅ PASS | Action item query is local (MongoDB). Email send requires network but is explicitly user-triggered. |
| III. Modularity | ✅ PASS | New EmailService module, independent of core voice pipeline. |
| IV. Simplicity (YAGNI) | ✅ PASS | Uses stdlib smtplib, no external email service SDKs. Plain text only. |
| V. Test-Driven Development | ✅ PASS | Will write tests first for email formatting, SMTP config validation. |
| VI. Benchmark-Driven Optimization | N/A | Not a performance-critical feature. |
| VII. Documentation-First | ✅ PASS | Will document .env variables in setup guide. |

**GATE RESULT**: All gates pass. Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/007-email-action-items/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal contracts only)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/
├── ara/
│   ├── email/                 # NEW: Email module
│   │   ├── __init__.py
│   │   ├── config.py          # EmailConfig from env vars
│   │   └── sender.py          # SMTPEmailSender service
│   ├── router/
│   │   ├── intent.py          # Add EMAIL_ACTION_ITEMS intent patterns
│   │   └── orchestrator.py    # Add _handle_email_action_items()
│   └── ...

tests/
├── unit/
│   ├── test_email_config.py   # NEW: Config validation tests
│   └── test_email_sender.py   # NEW: Email formatting tests
└── integration/
    └── test_email_flow.py     # NEW: End-to-end with mock SMTP
```

**Structure Decision**: Single project structure. New `email/` module under `src/ara/` following existing modularity patterns.

## Complexity Tracking

> No violations. All implementation uses stdlib and follows existing patterns.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | | |
