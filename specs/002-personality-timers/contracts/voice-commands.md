# Voice Command Contracts: Timer/Reminder System

**Feature**: 002-personality-timers
**Date**: 2026-01-14

## Reminder Commands

### Set Reminder

**Input Patterns**:
```
"remind me to [task] in [duration]"
"remind me in [duration] to [task]"
"set a reminder to [task] in [duration]"
"don't let me forget to [task]"
```

**Duration Formats**:
- Relative: "5 minutes", "1 hour", "30 seconds", "2 hours and 15 minutes"
- Absolute: "at 3 PM", "at 15:30", "tomorrow at 9 AM"

**Response Contract**:
```
Input: "remind me in 5 minutes to check the oven"
Current Time: 02:34 AM

Response: "Got it! It's 2:34 AM now, and I'll remind you at 2:39 AM to check the oven."
```

**Error Responses**:
| Condition | Response |
|-----------|----------|
| No duration specified | "When would you like me to remind you? Just say something like 'in 5 minutes' or 'at 3 PM'." |
| Duration is zero/negative | "Hmm, I can't set a reminder for the past! How about a few minutes from now?" |
| No task specified | "What would you like me to remind you about?" |

### List Reminders (Numbered Format)

**Input Patterns**:
```
"what reminders do I have"
"list my reminders"
"show my reminders"
"check my reminders"
```

**Response Contract (Multiple - Numbered)**:
```
Input: "what reminders do I have"

Response: "You've got 3 reminders coming up! First, you have a reminder at 2:39 AM to check the oven. Second, you have a reminder at 3:00 AM to call Mom. Third, you have a reminder at 3:15 AM to take out the trash."
```

**Response Contract (Single)**:
```
Input: "what reminders do I have"

Response: "You have one reminder at 2:39 AM to check the oven."
```

**Response Contract (None)**:
```
Input: "what reminders do I have"

Response: "Your schedule is clear - no reminders set right now!"
```

**Ordinal Number Format**:
- Use ordinal words: first, second, third, fourth, fifth, sixth, seventh, eighth, ninth, tenth
- For 11+, use numeric: "11th, you have a reminder..."
- Always list in chronological order by trigger time

### Cancel Reminder (By Description, Number, or Multiple)

**Input Patterns - By Description**:
```
"cancel my reminder about [task]"
"cancel the [task] reminder"
"delete my reminder"
"remove the reminder"
```

**Input Patterns - By Number**:
```
"delete reminder number [N]"
"cancel the [ordinal] reminder"
"remove reminder [N]"
"delete the third reminder"
"cancel reminder 5"
```

**Input Patterns - Multiple by Number**:
```
"delete reminders [N], [N], and [N]"
"cancel the third and sixth reminders"
"remove reminders 2, 4, and 5"
"delete the second, fourth, and seventh reminders"
```

**Response Contract (Success - By Description)**:
```
Input: "cancel my reminder about the oven"

Response: "Done! I've cancelled your reminder about the oven."
```

**Response Contract (Success - By Number)**:
```
Input: "delete reminder number 3"

Response: "Done! I've cancelled your third reminder - the one at 3:15 AM to take out the trash."
```

**Response Contract (Success - Multiple)**:
```
Input: "delete the third and sixth reminders"

Response: "Done! I've cancelled 2 reminders: the third one (take out the trash at 3:15 AM) and the sixth one (water the plants at 4:00 AM)."
```

**Response Contract (Invalid Number)**:
```
Input: "delete reminder number 10" (only 5 reminders exist)

Response: "Hmm, I only have 5 reminders right now. Want me to list them so you can pick the right one?"
```

**Response Contract (Ambiguous)**:
```
Input: "cancel my reminder" (multiple reminders exist)

Response: "You have a few reminders - which one should I cancel? You can say the reminder number, like 'cancel reminder 2', or describe it."
```

**Response Contract (Not Found)**:
```
Input: "cancel my reminder about the meeting"

Response: "I couldn't find a reminder about that. Want me to list what you have?"
```

### Clear All Reminders

**Input Patterns**:
```
"clear all reminders"
"delete all my reminders"
"remove all reminders"
"cancel all reminders"
```

**Response Contract (Success)**:
```
Input: "clear all reminders"

Response: "Done! I've cleared all 5 of your reminders. Fresh start!"
```

**Response Contract (None to Clear)**:
```
Input: "clear all reminders"

Response: "You don't have any reminders to clear - your schedule is already empty!"
```

## Timer Commands

### Set Timer

**Input Patterns**:
```
"set a timer for [duration]"
"start a timer for [duration]"
"[duration] timer"
"timer for [duration]"
```

**Response Contract**:
```
Input: "set a timer for 5 minutes"

Response: "Timer set! I'll let you know in 5 minutes."
```

### Query Timer

**Input Patterns**:
```
"how much time is left"
"what timers do I have"
"check my timer"
"time left on timer"
```

**Response Contract (Active)**:
```
Input: "how much time is left"

Response: "You've got 3 minutes and 20 seconds left on your timer."
```

**Response Contract (None)**:
```
Input: "what timers do I have"

Response: "No timers running right now. Want me to set one?"
```

### Cancel Timer

**Input Patterns**:
```
"cancel the timer"
"stop the timer"
"delete my timer"
```

**Response Contract**:
```
Input: "cancel the timer"

Response: "Timer cancelled!"
```

## Alert Notifications

### Timer Expiration

```
[FEEDBACK SOUND]
"Your timer is up!"
```

### Reminder Trigger

```
[FEEDBACK SOUND]
"Hey! Just a friendly reminder: [task]"
```

### Missed Reminder (On Startup)

```
"Oops! I meant to remind you earlier but I was rebooting. You wanted me to remind you to [task]."
```

## Personality Guidelines

All responses should:
1. Be concise (1-3 sentences for voice)
2. Start with the essential information
3. Add warmth through word choice (e.g., "Got it!", "Sure thing!")
4. Occasionally include playful elements when context allows
5. Never be condescending or overly cute
