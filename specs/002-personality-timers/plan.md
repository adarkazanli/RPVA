# Implementation Plan: Warm Personality with Timer/Reminder System

**Branch**: `002-personality-timers` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-personality-timers/spec.md`

## Summary

Replace the assistant's current personality with a warm, playful, and witty character (Purcobine). Add time-aware reminder confirmations that show both current time and target time. Implement reminder persistence to JSON file so reminders survive system restarts. Handle missed reminders by delivering them immediately on startup. Add numbered reminder listing and the ability to cancel reminders by number (single or multiple) or clear all reminders at once.

**Key Insight from Research**: The timer/reminder infrastructure already exists in `src/ara/commands/`. This feature primarily requires:
1. Adding persistence to the existing `ReminderManager`
2. Updating response formatting in the orchestrator
3. Configuring personality via system prompt
4. Adding numbered list format and cancel-by-number functionality
5. Adding clear-all-reminders functionality

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Ollama (existing), standard library (json, pathlib, datetime)
**Storage**: JSON file (`~/.ara/reminders.json`)
**Testing**: pytest
**Target Platform**: Raspberry Pi 4 (8GB RAM), Raspberry Pi OS (64-bit) Lite
**Project Type**: Single project (voice assistant)
**Performance Goals**: End-to-end response <6s, reminder save <100ms
**Constraints**: <6GB memory, offline-first, modular architecture
**Scale/Scope**: Single user, <100 concurrent reminders

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Pre-Design | Post-Design | Notes |
|-----------|------------|-------------|-------|
| I. Performance-First | PASS | PASS | JSON save is async, no latency impact |
| II. Offline-First | PASS | PASS | All local - JSON file, local LLM |
| III. Modularity | PASS | PASS | Persistence isolated to reminder module |
| IV. Simplicity (YAGNI) | PASS | PASS | JSON is simplest persistence option |
| V. Test-Driven Development | PENDING | PENDING | Tests required during implementation |
| VI. Benchmark-Driven | N/A | N/A | No performance-critical changes |
| VII. Documentation-First | PENDING | PENDING | Voice command reference update needed |

**Gate Status**: PASS - All principles satisfied or pending implementation-phase work.

## Project Structure

### Documentation (this feature)

```text
specs/002-personality-timers/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── voice-commands.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/ara/
├── commands/
│   ├── reminder.py          # MODIFY: Add persistence (save/load JSON)
│   └── timer.py             # NO CHANGE
├── config/
│   ├── loader.py            # MODIFY: Add personality config loading
│   ├── profiles.py          # MODIFY: Add PersonalityConfig
│   └── personality.py       # NEW: Personality configuration and prompts
├── router/
│   ├── orchestrator.py      # MODIFY: Time-aware responses, load reminders, set personality, numbered lists, cancel by number
│   └── intent.py            # MODIFY: Add REMINDER_CLEAR_ALL intent, extend cancel patterns for number references
└── llm/
    └── ollama.py            # NO CHANGE (uses existing set_system_prompt)

tests/
├── unit/
│   ├── test_reminder_persistence.py    # NEW
│   └── test_personality_responses.py   # NEW
└── integration/
    └── test_timer_reminder_flow.py     # MODIFY: Add persistence tests

~/.ara/
└── reminders.json       # NEW: Persisted reminders (created at runtime)
```

**Structure Decision**: Single project structure. This feature modifies existing modules rather than adding new architectural layers. All changes fit within the established `src/ara/` module hierarchy.

## Implementation Approach

### Component 1: Reminder Persistence

**Files**: `src/ara/commands/reminder.py`

**Changes**:
1. Add `persistence_path` parameter to `ReminderManager.__init__`
2. Add `_save()` method - serialize reminders to JSON
3. Add `_load()` method - deserialize reminders from JSON on startup
4. Call `_save()` after create, cancel, dismiss, trigger operations
5. Add `_handle_missed_reminders()` - check for and deliver past-due reminders

**Data Format**:
```json
{
  "version": 1,
  "reminders": [...]
}
```

### Component 2: Time-Aware Responses

**Files**: `src/ara/router/orchestrator.py`

**Changes**:
1. Modify `_handle_reminder_set()` to include current time in response
2. Update response format: "Got it! It's X:XX AM/PM now, and I'll remind you at Y:YY AM/PM to [task]."
3. Add local timezone formatting (UTC stored, local displayed)

### Component 3: Personality Configuration

**Files**:
- `src/ara/config/personality.py` (new)
- `src/ara/config/profiles.py` (modify)
- `src/ara/router/orchestrator.py` (modify)

**Changes**:
1. Create `PersonalityConfig` dataclass with name, system_prompt, warmth_level
2. Add default Purcobine personality prompt
3. Call `llm.set_system_prompt()` during orchestrator initialization
4. Update all timer/reminder response strings with warm language

### Component 4: Missed Reminder Handling

**Files**: `src/ara/router/orchestrator.py`, `src/ara/commands/reminder.py`

**Changes**:
1. On orchestrator startup, call `reminder_manager.check_missed()`
2. For each missed reminder, deliver with modified message explaining the delay
3. Mark as triggered after delivery

### Component 5: Numbered Reminder Listing

**Files**: `src/ara/router/orchestrator.py`

**Changes**:
1. Modify `_handle_reminder_query()` to format reminders with ordinal numbers
2. Add ordinal number utility (first, second, third... 11th, 12th, etc.)
3. Maintain chronological sort order for consistent numbering
4. Format: "First, you have a reminder at X:XX AM to [task]. Second, ..."

### Component 6: Cancel by Number

**Files**: `src/ara/router/orchestrator.py`, `src/ara/router/intent.py`

**Changes**:
1. Extend intent patterns to recognize "delete reminder number N" and ordinal forms
2. Add number extraction for single and multiple number inputs (e.g., "3", "third", "2, 4, and 5")
3. Modify `_handle_reminder_cancel()` to support cancel by index
4. Add validation for out-of-range numbers
5. Support multiple number cancellation in single command
6. Response includes confirmation of which reminder(s) were cancelled with details

### Component 7: Clear All Reminders

**Files**: `src/ara/router/orchestrator.py`, `src/ara/router/intent.py`, `src/ara/commands/reminder.py`

**Changes**:
1. Add REMINDER_CLEAR_ALL intent type to `IntentType` enum
2. Add intent patterns for "clear all reminders", "delete all my reminders"
3. Add `clear_all()` method to `ReminderManager`
4. Add `_handle_reminder_clear_all()` handler in orchestrator
5. Response includes count of reminders cleared

## Complexity Tracking

No constitution violations. All implementation uses existing patterns and minimal complexity.

## Next Steps

Run `/speckit.tasks` to generate the task list from this plan.
