# Implementation Plan: Timer Countdown Announcement

**Branch**: `003-timer-countdown` | **Date**: 2026-01-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-timer-countdown/spec.md`

## Summary

Add a 5-second verbal countdown before timer/reminder completion (e.g., "Ammar, you should start your call in 5..4..3..2..1..now"). Implement personalized announcements using the user's configured name and update the assistant's tone to be friendly but concise, removing excessive verbosity from responses.

**Key Insight**: The timer/reminder infrastructure from 002-personality-timers is fully functional. This feature primarily requires:
1. Adding countdown logic to the reminder check loop
2. Creating a user profile configuration for name storage
3. Updating personality prompts for concise tone
4. Handling overlapping countdown scenarios

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Ollama (existing), standard library (threading, time, datetime)
**Storage**: JSON file (`~/.ara/user_profile.json`) for user profile
**Testing**: pytest
**Target Platform**: Raspberry Pi 4 (8GB RAM), Raspberry Pi OS (64-bit) Lite
**Project Type**: Single project (voice assistant)
**Performance Goals**: Countdown timing accuracy <200ms variance per interval
**Constraints**: <6GB memory, offline-first, modular architecture
**Scale/Scope**: Single user, countdowns must not block main interaction loop

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Pre-Design | Post-Design | Notes |
|-----------|------------|-------------|-------|
| I. Performance-First | PASS | PASS | TTS latency <0.5s fits within 1-second countdown intervals |
| II. Offline-First | PASS | PASS | All local - TTS, user config, no cloud dependencies |
| III. Modularity | PASS | PASS | Countdown isolated to orchestrator callback |
| IV. Simplicity (YAGNI) | PASS | PASS | Minimal additions to existing infrastructure |
| V. Test-Driven Development | PENDING | PENDING | Tests required during implementation |
| VI. Benchmark-Driven | PASS | PASS | Timing accuracy testable with benchmarks |
| VII. Documentation-First | PENDING | PENDING | Voice command reference already exists |

**Gate Status**: PASS - All principles satisfied or pending implementation-phase work.

## Project Structure

### Documentation (this feature)

```text
specs/003-timer-countdown/
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
│   └── reminder.py          # NO CHANGE (countdown handled at orchestrator level)
├── config/
│   ├── loader.py            # MODIFY: Add get_user_profile_path()
│   ├── personality.py       # MODIFY: Update prompts for concise tone
│   └── user_profile.py      # NEW: User profile with name, preferences
├── router/
│   └── orchestrator.py      # MODIFY: Add countdown logic to reminder callback

tests/
├── unit/
│   ├── test_countdown.py         # NEW: Countdown timing and formatting
│   └── test_user_profile.py      # NEW: User profile load/save
└── integration/
    └── test_countdown_flow.py    # NEW: End-to-end countdown tests

~/.ara/
├── reminders.json           # EXISTING
└── user_profile.json        # NEW: User profile (name, preferences)
```

**Structure Decision**: Single project structure. This feature extends existing orchestrator with countdown callback logic. User profile is a new small module for name configuration.

## Implementation Approach

### Component 1: User Profile Configuration

**Files**: `src/ara/config/user_profile.py` (new), `src/ara/config/loader.py`

**Changes**:
1. Create `UserProfile` dataclass with `name: str | None` and `preferences: dict`
2. Add `load_user_profile()` and `save_user_profile()` functions
3. Store in `~/.ara/user_profile.json`
4. Add `get_user_profile_path()` to loader.py

**Data Format**:
```json
{
  "version": 1,
  "name": "Ammar",
  "preferences": {}
}
```

### Component 2: Countdown Announcement Logic

**Files**: `src/ara/router/orchestrator.py`

**Changes**:
1. Add `_countdown_active: dict[UUID, bool]` to track active countdowns
2. Modify `_check_timers_and_reminders()` to detect 5-second threshold
3. Add `_start_countdown(reminder)` method that:
   - Generates countdown phrase: "[Name], you should [task] in 5..4..3..2..1..now"
   - Uses TTS to speak each number at 1-second intervals
   - Handles cancellation during countdown
4. Add `_combine_countdowns(reminders)` for overlapping timers
5. Load user profile in `__init__` for personalized name

**Countdown Flow**:
```
t=-5s: Detect reminder approaching → start countdown
t=-5s: Speak "[Name], you should [task] in 5..."
t=-4s: Speak "4..."
t=-3s: Speak "3..."
t=-2s: Speak "2..."
t=-1s: Speak "1..."
t=0s:  Speak "now."
```

### Component 3: Concise Personality Tone

**Files**: `src/ara/config/personality.py`

**Changes**:
1. Update `DEFAULT_PERSONALITY.system_prompt` to emphasize brevity:
   - Remove "playful" and "witty" emphasis
   - Add explicit instruction: "Keep responses to one sentence when possible"
   - Remove phrases like "I'd be delighted" from examples
2. Maintain warmth without verbosity

**Updated Prompt (excerpt)**:
```
You are Purcobine, a warm and helpful voice assistant. Be:
- Warm: Use friendly language but keep it brief
- Clear: One sentence is better than three
- Direct: Give information without filler phrases

Bad: "Oh how wonderful! I'd be happy to help you with that!"
Good: "Got it!"
```

### Component 4: Overlapping Countdown Handling

**Files**: `src/ara/router/orchestrator.py`

**Changes**:
1. Add `_get_upcoming_reminders(seconds: int)` to find reminders within window
2. When multiple reminders within 5-second window:
   - Combine task descriptions: "[Name], you should [task1] and [task2] in 5..4..3..2..1..now"
   - Mark all as handled after "now"
3. Prevent duplicate countdown announcements

### Component 5: Timer Cancellation During Countdown

**Files**: `src/ara/router/orchestrator.py`

**Changes**:
1. Check `_countdown_active[reminder.id]` before each number
2. If reminder cancelled mid-countdown, stop speaking
3. Clean up tracking dict after countdown completes

## Complexity Tracking

No constitution violations. All implementation uses existing patterns and minimal complexity.

## Next Steps

Run `/speckit.tasks` to generate the task list from this plan.
