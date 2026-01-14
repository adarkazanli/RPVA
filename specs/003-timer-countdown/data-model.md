# Data Model: Timer Countdown Announcement

**Feature**: 003-timer-countdown
**Date**: 2026-01-14

## Entities

### UserProfile

User configuration for personalized announcements.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| version | int | Schema version | Always 1 |
| name | string \| null | User's name for announcements | Optional, max 50 chars |
| preferences | object | Reserved for future settings | Empty object initially |

**Storage**: `~/.ara/user_profile.json`

**Example**:
```json
{
  "version": 1,
  "name": "Ammar",
  "preferences": {}
}
```

**Validation Rules**:
- `name` if provided must be non-empty string, trimmed of whitespace
- `version` must be 1 (future versions may add migration)
- File may not exist (use defaults)

### CountdownState (In-Memory Only)

Tracks active countdown to handle cancellation.

| Field | Type | Description |
|-------|------|-------------|
| reminder_ids | set[UUID] | IDs of reminders in current countdown |
| cancelled | bool | Whether countdown was cancelled |
| current_number | int | Current countdown position (5→1) |

**Note**: Not persisted. Exists only during active countdown.

## State Transitions

### Reminder with Countdown

```
PENDING → (5s threshold) → COUNTDOWN_ACTIVE → (countdown complete) → TRIGGERED → DISMISSED/CANCELLED

States:
- PENDING: Normal reminder waiting
- COUNTDOWN_ACTIVE: 5-second countdown in progress (transient, not stored)
- TRIGGERED: Countdown completed, reminder fired
- DISMISSED/CANCELLED: Final states (existing)
```

**Transitions**:
1. `PENDING → COUNTDOWN_ACTIVE`: When `remind_at - now <= 5 seconds`
2. `COUNTDOWN_ACTIVE → TRIGGERED`: After "now" is spoken
3. `COUNTDOWN_ACTIVE → CANCELLED`: If user cancels during countdown
4. `TRIGGERED → DISMISSED`: After user acknowledges

## Relationships

```
UserProfile (1) ←──uses── Orchestrator (1)
                              │
                              │ manages
                              ▼
                         Reminder (*)
                              │
                              │ triggers
                              ▼
                      CountdownState (0..1)
```

## Data Flow

### Countdown Initiation

```
1. Check thread detects: remind_at - now <= 5s
2. Load UserProfile.name (cached)
3. Get all reminders within 5s window
4. Create CountdownState with reminder_ids
5. Generate phrase: "[name], you should [tasks] in 5..."
6. Begin TTS sequence
```

### Cancellation During Countdown

```
1. User says "cancel reminder X"
2. Main thread calls reminder_manager.cancel(id)
3. Sets CountdownState.cancelled = True
4. Check thread sees cancelled flag
5. Stops countdown immediately (no "now")
```

## Migration Notes

### From 002-personality-timers

No migration required. Existing reminders.json format unchanged. UserProfile is additive.

### Default Values

| Scenario | Behavior |
|----------|----------|
| No user_profile.json | Use "Hey" as generic address |
| name is null | Use "Hey" as generic address |
| name is empty string | Use "Hey" as generic address |

## Schema Versioning

**Current Version**: 1

Future versions may add:
- Multiple user profiles
- Countdown preferences (enable/disable, countdown length)
- Voice selection per user

Version migrations will be handled in `load_user_profile()` with backward compatibility.
