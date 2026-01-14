# Voice Commands: Timer Countdown Announcement

**Feature**: 003-timer-countdown
**Date**: 2026-01-14

## New Commands

### Set User Name

Configure the user's name for personalized countdown announcements.

**Trigger Phrases**:
- "My name is [name]"
- "Call me [name]"
- "Set my name to [name]"

**Entity Extraction**:
- `name`: String following trigger phrase

**Response Pattern**:
```
Input: "My name is Ammar"
Output: "Got it, Ammar! I'll use your name from now on."

Input: "Call me Sarah"
Output: "Noted, Sarah! Nice to meet you."
```

**Error Handling**:
```
Input: "My name is" (no name provided)
Output: "What should I call you?"
```

## Modified Commands

### Reminder Set (Updated Response)

Existing command, updated for concise tone.

**Previous Response**:
```
"Oh wonderful! It's 2:34 PM right now, and I'd be happy to remind you at 2:39 PM to check the oven. Consider it done!"
```

**New Response**:
```
"Got it! I'll remind you at 2:39 PM to check the oven."
```

### Reminder List (Updated Response)

Existing command, updated for concise tone.

**Previous Response**:
```
"Let me take a look at what you've got coming up! You've got 2 reminders. First, you have a reminder at 3:18 PM to check the oven. Second, you have a reminder at 3:25 PM to call Mom. Is there anything else I can help you with?"
```

**New Response**:
```
"You have 2 reminders. First, at 3:18 PM to check the oven. Second, at 3:25 PM to call Mom."
```

## Countdown Announcement (System-Initiated)

Not a user command - system initiates this 5 seconds before reminder triggers.

**Format**:
```
Single reminder:
"[Name], you should [task] in 5... 4... 3... 2... 1... now."

Multiple reminders (combined):
"[Name], you should [task1] and [task2] in 5... 4... 3... 2... 1... now."

No name configured:
"Hey, you should [task] in 5... 4... 3... 2... 1... now."
```

**Timing**:
- Each number spoken at 1-second intervals
- Total duration: ~6 seconds (intro + 5 numbers + "now")

**Edge Cases**:

| Scenario | Behavior |
|----------|----------|
| Timer < 5s | Start from remaining time (e.g., "3... 2... 1... now") |
| Cancelled mid-countdown | Stop immediately, no "now" |
| TTS failure | Log error, skip to normal trigger |

## Intent Classification Updates

### New Intent: USER_NAME_SET

```python
class IntentType(Enum):
    # ... existing intents ...
    USER_NAME_SET = "user_name_set"
```

**Patterns**:
```python
USER_NAME_SET_PATTERNS = [
    r"my name is (\w+)",
    r"call me (\w+)",
    r"set my name to (\w+)",
    r"i'm (\w+)",  # Handle contractions
]
```

**Entity Extraction**:
```python
{
    "name": str  # Extracted user name
}
```

## Response Tone Guidelines

All responses should follow these principles:

### Do

- One sentence when possible
- Start with action confirmation ("Got it", "Done", "Noted")
- Include essential information only
- Use contractions ("I'll" not "I will")

### Don't

- Multiple exclamation points
- Filler phrases ("I'd be happy to", "Let me just", "Oh wonderful")
- Asking follow-up questions unless needed
- Repeating what the user said

### Examples

| Scenario | Bad | Good |
|----------|-----|------|
| Set reminder | "Absolutely! I'd be delighted to help you with that reminder. It's currently 3:00 PM and I'll remind you at 3:05 PM to call Mom!" | "Got it! Reminder set for 3:05 PM." |
| Cancel reminder | "Sure thing! I've gone ahead and cancelled that reminder for you. Is there anything else I can help with?" | "Done! Cancelled your reminder to call Mom." |
| List empty | "Let me check... It looks like you don't have any reminders set right now! Would you like to create one?" | "No reminders set." |

## Implementation Status

**Status**: Implemented

### Files Modified

| File | Changes |
|------|---------|
| `src/ara/router/intent.py` | Added `USER_NAME_SET` intent type and patterns |
| `src/ara/router/orchestrator.py` | Added countdown logic, user name handling, concise responses |
| `src/ara/config/personality.py` | Updated to concise tone with examples |
| `src/ara/config/user_profile.py` | New file for user profile persistence |
| `src/ara/config/loader.py` | Added `get_user_profile_path()` function |

### Test Coverage

- Unit tests: `tests/unit/test_countdown.py`, `tests/unit/test_user_profile.py`, `tests/unit/test_personality_responses.py`
- Integration tests: `tests/integration/test_countdown_flow.py`
