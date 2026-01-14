# Research: Timer Countdown Announcement

**Feature**: 003-timer-countdown
**Date**: 2026-01-14

## Research Questions

### 1. Countdown Timing Accuracy with Piper TTS

**Context**: Each countdown number needs to be spoken at 1-second intervals. Piper TTS latency budget is 0.5s per the constitution.

**Finding**: Piper TTS with medium voice synthesizes short phrases (single numbers, single words) in under 200ms on Raspberry Pi 4. Combined with the existing audio playback (~100ms for short clips), we have ~700ms margin within each 1-second interval.

**Decision**: Pre-synthesize countdown numbers ("5", "4", "3", "2", "1", "now") at startup to eliminate TTS latency during countdown.

**Rationale**: Pre-synthesis ensures timing accuracy and eliminates variance from TTS processing. This follows the constitution's performance-first principle.

**Alternatives Considered**:
- Real-time TTS for each number: Rejected due to timing variance risk
- Pre-recorded audio files: Rejected as it adds maintenance burden for different voices

### 2. User Profile Storage Location

**Context**: Need to store user's name for personalized announcements.

**Finding**: The existing `~/.ara/` directory pattern (used for reminders.json) provides a consistent location for user configuration.

**Decision**: Store user profile in `~/.ara/user_profile.json` using the same pattern as reminders.json.

**Rationale**: Consistent with existing patterns, simple JSON format, no new dependencies.

**Alternatives Considered**:
- Environment variable: Rejected as it requires system configuration
- Config file in repo: Rejected as user-specific data shouldn't be in source control
- Merge into existing config: Rejected to maintain separation of concerns

### 3. Countdown Thread Safety

**Context**: Countdown runs in the background check thread while main voice loop may receive cancellation commands.

**Finding**: The existing `_check_timers_and_reminders()` loop already runs in a daemon thread. Using a simple dict to track countdown state with atomic bool checks is sufficient for single-threaded countdown operations.

**Decision**: Use `_countdown_active: dict[UUID, bool]` with simple checks, no locks needed.

**Rationale**: Python's GIL ensures atomic dict operations. Countdown runs sequentially in the check thread, and cancellation sets the flag from the main thread. The simplicity aligns with YAGNI principle.

**Alternatives Considered**:
- Full threading.Lock protection: Rejected as over-engineering for single-threaded countdown
- asyncio approach: Rejected as it would require architectural changes

### 4. Concise Tone Guidelines

**Context**: User requested "friendly but not over-friendly" responses.

**Finding**: Analysis of current personality prompt shows explicit instructions for "playful", "witty", and "add personality" which encourage verbosity.

**Decision**: Update personality prompt to prioritize brevity while maintaining warmth:
- Remove "playful" and "witty" instructions
- Add explicit examples of bad (verbose) vs good (concise) responses
- Keep "warm" instruction but emphasize single-sentence responses

**Rationale**: The prompt directly controls LLM output style. Explicit before/after examples are most effective for guiding behavior.

**Alternatives Considered**:
- Multiple personality profiles: Rejected as adds complexity without benefit
- Post-processing to shorten responses: Rejected as inefficient and unpredictable

### 5. Overlapping Countdown Handling

**Context**: Multiple reminders might trigger within the same 5-second window.

**Finding**: The spec clarifies that overlapping countdowns should be combined into a single announcement with multiple tasks.

**Decision**: Check for all reminders within 5-second window at countdown start, combine task descriptions using "and" conjunction.

**Rationale**: User-specified requirement. Combining is natural language approach.

**Alternatives Considered**:
- Sequential countdowns: Rejected per user requirement
- Skip later countdowns: Rejected as would miss reminders

## Technical Decisions Summary

| Area | Decision | Key Reason |
|------|----------|------------|
| TTS Timing | Pre-synthesize numbers | Performance accuracy |
| User Profile | `~/.ara/user_profile.json` | Consistent patterns |
| Thread Safety | Simple dict tracking | YAGNI, sufficient |
| Tone | Update prompt, remove verbosity | Direct control |
| Overlapping | Combine task descriptions | User requirement |

## Dependencies Confirmed

- **Piper TTS**: Existing, no changes needed
- **JSON Storage**: Standard library, existing pattern
- **Threading**: Standard library, existing pattern
- **Orchestrator**: Existing module, will be extended

## No Further Research Required

All technical questions resolved. Ready for Phase 1 design.
