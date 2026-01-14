# Quickstart: Warm Personality with Timer/Reminder System

**Feature**: 002-personality-timers
**Date**: 2026-01-14

## Overview

This feature enhances the Ara voice assistant with:
1. **Warm, playful, witty personality** - Purcobine responds with friendly, engaging language
2. **Time-aware reminders** - Confirmations include current time and target time
3. **Persistent reminders** - Reminders survive system restarts
4. **Multiple concurrent timers** - Users can manage several timers/reminders simultaneously

## Prerequisites

- Existing Ara voice assistant setup (see `ara-voice-assistant-pi4-setup.md`)
- Ollama running with configured model
- No additional dependencies required

## Key Changes

### 1. Personality Configuration

The assistant now uses a system prompt to establish personality:

```python
# Configured at startup in orchestrator
llm.set_system_prompt("""
You are Purcobine, a warm, playful, and witty voice assistant...
""")
```

### 2. Reminder Persistence

Reminders are now saved to `~/.ara/reminders.json`:

```python
# ReminderManager handles persistence automatically
reminder_manager = ReminderManager(
    on_trigger=on_reminder_trigger,
    persistence_path="~/.ara/reminders.json"
)
```

### 3. Time-Aware Confirmations

When setting reminders, the response includes both times:

```
User: "Remind me in 5 minutes to check the oven"
Response: "Got it! It's 2:34 AM now, and I'll remind you at 2:39 AM to check the oven."
```

## Usage Examples

### Setting a Reminder

```
User: "Purcobine, remind me in 10 minutes to take out the laundry"
Purcobine: "Got it! It's 10:15 PM now, and I'll remind you at 10:25 PM to take out the laundry."
```

### Listing Reminders

```
User: "What reminders do I have?"
Purcobine: "You've got 2 reminders coming up! First, at 10:25 PM: take out the laundry. Then at 11:00 PM: call Mom."
```

### Canceling a Reminder

```
User: "Cancel my reminder about the laundry"
Purcobine: "Done! I've cancelled your reminder about the laundry."
```

### Setting Multiple Timers

```
User: "Set a timer for 5 minutes"
Purcobine: "Timer set! I'll let you know in 5 minutes."

User: "Set another timer for 10 minutes"
Purcobine: "Another timer? You got it! 10 minutes starting now."
```

## Testing

Run the test suite:

```bash
cd src
python -m pytest tests/unit/test_reminder_persistence.py -v
python -m pytest tests/unit/test_personality.py -v
python -m pytest tests/integration/test_timer_reminder_flow.py -v
```

## File Structure

```
src/ara/
├── commands/
│   ├── reminder.py          # Extended with persistence
│   └── timer.py             # Unchanged
├── config/
│   └── personality.py       # New: personality configuration
├── router/
│   └── orchestrator.py      # Updated response formatting
└── llm/
    └── ollama.py            # Unchanged (uses existing set_system_prompt)

~/.ara/
└── reminders.json           # Persisted reminders
```

## Troubleshooting

### Reminders not persisting

1. Check that `~/.ara/` directory exists and is writable
2. Check file permissions: `ls -la ~/.ara/reminders.json`
3. Review logs for persistence errors

### Personality not showing

1. Verify system prompt is being set: check orchestrator logs
2. Ensure Ollama is responding (not falling back to mock)
3. Test LLM directly: `python -c "from ara.llm import create_language_model; ..."`

### Time showing incorrectly

1. Check system timezone: `date`
2. Ensure UTC conversion is working: times are stored in UTC, displayed in local
