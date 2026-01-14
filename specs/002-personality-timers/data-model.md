# Data Model: Warm Personality with Timer/Reminder System

**Feature**: 002-personality-timers
**Date**: 2026-01-14

## Entities

### Reminder (Extended)

The existing `Reminder` entity in `src/ara/commands/reminder.py` is extended with persistence.

```
Reminder
├── id: UUID                       # Unique identifier
├── message: str                   # Task description to remind about
├── remind_at: datetime (UTC)      # Target trigger time
├── recurrence: Recurrence         # NONE | DAILY | WEEKLY | MONTHLY
├── status: ReminderStatus         # PENDING | TRIGGERED | DISMISSED | CANCELLED
├── triggered_at: datetime | None  # When actually triggered
├── created_by_interaction: UUID   # Interaction that created this
└── created_at: datetime (UTC)     # Creation timestamp
```

**Persistence Schema** (`~/.ara/reminders.json`):
```json
{
  "version": 1,
  "reminders": [
    {
      "id": "uuid-string",
      "message": "check the oven",
      "remind_at": "2026-01-14T02:39:00Z",
      "recurrence": "none",
      "status": "pending",
      "triggered_at": null,
      "created_by_interaction": "uuid-string",
      "created_at": "2026-01-14T02:34:00Z"
    }
  ]
}
```

### Timer (Existing - No Changes)

The existing `Timer` entity remains unchanged. Timers are session-based and do not persist (they are typically short-duration).

```
Timer
├── id: UUID
├── name: str | None
├── duration_seconds: int
├── started_at: datetime
├── expires_at: datetime
├── status: TimerStatus
├── alert_played: bool
└── created_by_interaction: UUID
```

### PersonalityConfig (New)

Configuration for the assistant's personality traits.

```
PersonalityConfig
├── name: str                  # Assistant name (e.g., "Purcobine")
├── system_prompt: str         # Full system prompt for LLM
├── warmth_level: str          # "friendly" | "caring" | "professional"
└── wit_enabled: bool          # Whether to include witty elements
```

**Default Configuration**:
```python
PersonalityConfig(
    name="Purcobine",
    system_prompt="""You are Purcobine, a warm, playful, and witty voice assistant. Your personality is:
- Warm: Use friendly, caring language. Address the user kindly.
- Playful: Include light humor when appropriate. Keep things fun but not distracting.
- Witty: Use clever phrasing and occasional wordplay. Be quick and smart with responses.

Keep responses concise (1-3 sentences) since you're a voice assistant. Always be helpful first, then add personality. If delivering reminders or timer alerts, be clear about the information but add warmth.""",
    warmth_level="friendly",
    wit_enabled=True
)
```

## State Transitions

### Reminder Lifecycle

```
     ┌──────────────────────────────────────┐
     │                                      │
     ▼                                      │
[PENDING] ──────────► [TRIGGERED] ──────► [DISMISSED]
     │                     │
     │                     │ (if recurring)
     │                     ▼
     │               [NEW PENDING]
     │
     └──────────────► [CANCELLED]
```

**Transition Events**:
- PENDING → TRIGGERED: `remind_at <= now` (automatic via background check)
- TRIGGERED → DISMISSED: User acknowledges reminder
- PENDING → CANCELLED: User cancels before trigger
- TRIGGERED → NEW PENDING: For recurring reminders, create next occurrence

### Timer Lifecycle (Existing)

```
[RUNNING] ─────► [COMPLETED]
     │
     ▼
[PAUSED] ──────► [RUNNING]
     │
     │
[CANCELLED] ◄────┘
```

## Validation Rules

### Reminder Validation

| Field | Rule |
|-------|------|
| message | Required, non-empty, max 500 characters |
| remind_at | Must be in future (or reject with error) |
| recurrence | Must be valid enum value |

### Time Parsing Rules

Relative durations supported:
- "in X minutes/hours/seconds"
- "in X min/hr/sec"

Absolute times supported:
- "at HH:MM AM/PM"
- "at HH:MM" (24-hour)
- "tomorrow at HH:MM"

## Relationships

```
User
 │
 ├───< Reminder (one-to-many via interaction)
 │
 ├───< Timer (one-to-many via interaction)
 │
 └─── PersonalityConfig (one-to-one, global)
```

## Data Volume Assumptions

- Expected: <100 active reminders per user
- Storage: Single JSON file, ~50KB max
- Memory: All reminders loaded into memory at startup
- Persistence: Save after each mutation (create/cancel/trigger)
