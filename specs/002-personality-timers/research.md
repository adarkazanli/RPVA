# Research: Warm Personality with Timer/Reminder System

**Feature**: 002-personality-timers
**Date**: 2026-01-14

## Technical Context Findings

### Existing Infrastructure

**Timer/Reminder System Already Exists**:
- `src/ara/commands/reminder.py` - Full `ReminderManager` class with create, cancel, list, trigger callbacks
- `src/ara/commands/timer.py` - Full `TimerManager` class with create, cancel, pause, resume, query
- `src/ara/router/intent.py` - Intent classifier already handles TIMER_SET, TIMER_CANCEL, TIMER_QUERY, REMINDER_SET, REMINDER_CANCEL, REMINDER_QUERY
- `src/ara/router/orchestrator.py` - Already integrates timer/reminder managers with voice pipeline

**What's Missing**:
1. **Persistence** - Current implementation stores reminders in memory only (no file persistence)
2. **Time-aware confirmations** - Response text doesn't include current time + calculated target time
3. **Warm personality** - No system prompt configured for personality
4. **Missed reminder handling** - No logic for reminders that trigger during downtime

### Key Files to Modify

| File | Change Required |
|------|-----------------|
| `src/ara/commands/reminder.py` | Add persistence (save/load to JSON file) |
| `src/ara/router/orchestrator.py` | Update response formatting for time-aware confirmations, load reminders on startup |
| `src/ara/llm/ollama.py` (or personality module) | Configure warm/playful/witty system prompt |
| `src/ara/config/profiles.py` | Add personality configuration |

### Persistence Strategy

**Decision**: JSON file persistence
**Rationale**:
- Simplest approach aligning with YAGNI (Principle IV)
- Human-readable for debugging
- No external dependencies
- Fast enough for expected scale (<100 reminders)

**Alternatives Considered**:
- SQLite: Overkill for single-user local storage
- Pickle: Security concerns, not human-readable

**Implementation**:
- Save file: `~/.ara/reminders.json`
- Format: Array of reminder objects with all fields
- Save on: create, cancel, dismiss, trigger
- Load on: orchestrator initialization

### Personality System Prompt

**Decision**: Configure via system prompt in LLM
**Rationale**:
- `OllamaLanguageModel` already supports `set_system_prompt()`
- No code changes needed to LLM module
- Can be configured at startup

**Proposed System Prompt**:
```
You are Purcobine, a warm, playful, and witty voice assistant. Your personality is:
- Warm: Use friendly, caring language. Address the user kindly.
- Playful: Include light humor when appropriate. Keep things fun but not distracting.
- Witty: Use clever phrasing and occasional wordplay. Be quick and smart with responses.

Keep responses concise (1-3 sentences) since you're a voice assistant. Always be helpful first, then add personality. If delivering reminders or timer alerts, be clear about the information but add warmth.
```

### Time-Aware Response Format

**Decision**: Modify `_handle_reminder_set()` to include both current time and target time
**Rationale**: User explicitly requested this format ("It is 2:34am, I will remind you at 2:39am")

**Current Format**: "Reminder set for 02:39 AM: check the oven"
**New Format**: "Got it! It's 2:34 AM now, and I'll remind you at 2:39 AM to check the oven."

### Missed Reminder Handling

**Decision**: Deliver immediately on startup with note about delay
**Rationale**:
- User should still receive the reminder (better late than never)
- Transparency about the delay maintains trust

**Implementation**:
- On load, check each reminder's `remind_at` vs current time
- If `remind_at < now`, mark as triggered and deliver immediately
- Response: "Hey! You asked me to remind you to [task] - I was rebooting, but here it is now!"

## Constitution Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Performance-First | Compliant | No new latency impact - JSON save is async, personality prompt adds ~0 tokens to generation |
| II. Offline-First | Compliant | All features work locally, JSON stored locally |
| III. Modularity | Compliant | Persistence isolated to reminder module, personality via config |
| IV. Simplicity (YAGNI) | Compliant | JSON persistence is simplest solution, no over-engineering |
| V. Test-Driven Development | Pending | Will require tests for persistence and time-aware formatting |
| VI. Benchmark-Driven | N/A | No performance-critical changes |
| VII. Documentation-First | Pending | Will need to update voice command reference |

## Dependencies

No new dependencies required. All functionality uses existing Python standard library.

## Unknowns Resolved

| Unknown | Resolution |
|---------|------------|
| Persistence mechanism | JSON file at `~/.ara/reminders.json` |
| Personality implementation | System prompt configured at startup |
| Time format in responses | Include both current time and target time |
| Missed reminder behavior | Deliver immediately on startup with explanation |
