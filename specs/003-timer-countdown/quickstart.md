# Quickstart: Timer Countdown Announcement

**Feature**: 003-timer-countdown
**Date**: 2026-01-14

## Prerequisites

- 002-personality-timers feature must be implemented and functional
- Python 3.11+ installed
- pytest for running tests

## Setup

### 1. Configure Your Name (Optional)

Create or edit `~/.ara/user_profile.json`:

```json
{
  "version": 1,
  "name": "Ammar",
  "preferences": {}
}
```

Or set via voice command after implementation:
```
"My name is Ammar"
```

### 2. Verify Existing Setup

Ensure the reminder system works:

```bash
cd /Users/adarkazanli/Projects/mpsinc/11-RPVA
python -m pytest tests/ -k reminder -v
```

## Testing the Feature

### Manual Testing

1. **Test countdown with name**:
   ```
   You: "Remind me in 10 seconds to test the countdown"
   Assistant: "Got it! Reminder set for [time]."
   (5 seconds before) Assistant: "Ammar, you should test the countdown in 5... 4... 3... 2... 1... now."
   ```

2. **Test countdown without name** (delete user_profile.json first):
   ```
   You: "Remind me in 10 seconds to check something"
   Assistant: "Got it! Reminder set for [time]."
   (5 seconds before) Assistant: "Hey, you should check something in 5... 4... 3... 2... 1... now."
   ```

3. **Test short timer** (less than 5 seconds):
   ```
   You: "Remind me in 3 seconds to wave"
   Assistant: "Got it! Reminder set for [time]."
   (immediately) Assistant: "Ammar, you should wave in 3... 2... 1... now."
   ```

4. **Test cancellation during countdown**:
   ```
   You: "Remind me in 10 seconds to do something"
   (wait 6 seconds)
   Assistant: "Ammar, you should do something in 5... 4..."
   You: "Cancel my reminder"
   (countdown stops, no "now")
   ```

5. **Test combined countdown** (set two reminders close together):
   ```
   You: "Remind me in 10 seconds to call mom"
   You: "Remind me in 12 seconds to check email"
   (5 seconds before first) Assistant: "Ammar, you should call mom and check email in 5... 4... 3... 2... 1... now."
   ```

### Automated Testing

Run the test suite:

```bash
# Unit tests
python -m pytest tests/unit/test_countdown.py -v
python -m pytest tests/unit/test_user_profile.py -v

# Integration tests
python -m pytest tests/integration/test_countdown_flow.py -v

# All countdown-related tests
python -m pytest tests/ -k countdown -v
```

### Timing Accuracy Test

```bash
# Run timing benchmark
python -m pytest tests/unit/test_countdown.py::test_countdown_timing_accuracy -v
```

Expected: Each interval within 200ms of target 1-second spacing.

## Concise Tone Verification

Test that responses are brief:

```
You: "Set a reminder for 5 minutes to call mom"
Expected: "Got it! Reminder set for [time]." (not verbose)
NOT: "Oh wonderful! I'd be happy to set that reminder for you!"

You: "What reminders do I have?"
Expected: "You have 1 reminder at [time] to call mom." (concise)
NOT: "Let me check what you've got coming up! You have..."
```

## Files Changed

| File | Change |
|------|--------|
| `src/ara/config/user_profile.py` | NEW - User profile dataclass and load/save |
| `src/ara/config/loader.py` | Add `get_user_profile_path()` |
| `src/ara/config/personality.py` | Update prompt for concise tone |
| `src/ara/router/orchestrator.py` | Add countdown logic |
| `src/ara/router/intent.py` | Add USER_NAME_SET intent |
| `tests/unit/test_countdown.py` | NEW - Countdown unit tests |
| `tests/unit/test_user_profile.py` | NEW - Profile tests |
| `tests/integration/test_countdown_flow.py` | NEW - E2E tests |

## Troubleshooting

### Countdown Not Starting

1. Check reminder is pending: `python -c "from ara.commands.reminder import ReminderManager; rm = ReminderManager(persistence_path='~/.ara/reminders.json'); print(rm.list_pending())"`
2. Verify background thread is running (check logs)
3. Ensure TTS is working: test with simple phrase

### Wrong Name or No Name

1. Check file exists: `cat ~/.ara/user_profile.json`
2. Verify JSON format is valid
3. Restart assistant to reload profile

### Timing Drift

1. Check system load during countdown
2. Verify Piper TTS latency: should be <200ms per number
3. Run timing benchmark to measure variance

## Next Steps

After implementing and testing:

1. Update voice command reference documentation
2. Run full test suite to verify no regressions
3. Test on Raspberry Pi 4 hardware for timing accuracy
