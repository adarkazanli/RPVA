# Voice Command Reference

**Ara Voice Assistant**
**Last Updated**: 2026-01-21

This document provides a comprehensive reference for all supported voice commands.

---

## Claude Query Commands (Feature: 009-claude-query-mode)

### Ask Claude a Question

**Input Patterns**:
```
"ask Claude [question]"
"ask Claude about [topic]"
"tell Claude [message]"
"Claude [question]"
"have Claude [task]"
"get Claude's opinion on [topic]"
```

**Response Contract**:
```
Input: "ask Claude what is the capital of France"

[WAITING SOUND PLAYS]
Response: "Paris is the capital of France."
```

**Notes**:
- Responses are optimized for voice (~150 words or less)
- A waiting sound plays while Claude is thinking
- Follow-up questions can be asked within 5 seconds without trigger phrase

### Follow-up Questions (Within 5-Second Window)

**After receiving a Claude response**:
```
[No trigger phrase needed within 5 seconds]
"What else can you tell me?"
"Can you explain more?"
"Why is that?"
```

**Response Contract**:
```
Initial: "ask Claude what is Python"
Response: "Python is a programming language..."

[Within 5 seconds]
Follow-up: "What are its main features?"
Response: "Python's main features include..."
```

### Summarize Claude Conversations

**Input Patterns**:
```
"summarize my Claude conversations today"
"summarize my Claude conversations yesterday"
"summarize my Claude conversations this week"
"summarize my Claude conversations this month"
"what did I ask Claude today"
"what did we discuss with Claude this week"
```

**Response Contract (With History)**:
```
Input: "summarize my Claude conversations today"

Response: "You had 3 conversations with Claude today:
1. Asked: What is the capital of France?
   Claude: Paris is the capital of France.
2. Asked: How do I make pasta?
   Claude: To make pasta, boil water and add salt..."
```

**Response Contract (No History)**:
```
Input: "summarize my Claude conversations today"

Response: "You haven't had any Claude conversations today."
```

### Start New Conversation (Reset)

**Input Patterns**:
```
"new conversation"
"start over"
"start fresh"
"reset conversation"
"clear conversation"
"clear conversation history"
"forget our conversation"
"let's start fresh"
```

**Response Contract (With History)**:
```
Input: "new conversation"

Response: "I've cleared our conversation history. What would you like to talk about?"
```

**Response Contract (No History)**:
```
Input: "new conversation"

Response: "Starting a new conversation. How can I help you?"
```

### Error Responses

| Condition | Response |
|-----------|----------|
| API key not configured | "To use Claude, please set up your API key. Set the ANTHROPIC_API_KEY environment variable with your Claude API key." |
| Network unavailable | "I can't reach Claude right now. Please check your internet connection and try again." |
| Request timeout | "Claude is taking longer than expected to respond. Would you like me to try again?" |

---

## Timer Commands (Feature: 002-personality-timers)

### Set Timer

**Input Patterns**:
```
"set a timer for [duration]"
"start a timer for [duration]"
"[duration] timer"
"timer for [duration]"
```

**Duration Formats**: 5 minutes, 1 hour, 30 seconds, 2 hours and 15 minutes

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

**Response Contract**:
```
Input: "how much time is left"

Response: "You've got 3 minutes and 20 seconds left on your timer."
```

### Cancel Timer

**Input Patterns**:
```
"cancel the timer"
"stop the timer"
"delete my timer"
```

---

## Reminder Commands (Feature: 002-personality-timers)

### Set Reminder

**Input Patterns**:
```
"remind me to [task] in [duration]"
"remind me in [duration] to [task]"
"set a reminder to [task] in [duration]"
"don't let me forget to [task]"
```

**Duration Formats**:
- Relative: "5 minutes", "1 hour", "30 seconds"
- Absolute: "at 3 PM", "at 15:30", "tomorrow at 9 AM"

**Response Contract**:
```
Input: "remind me in 5 minutes to check the oven"

Response: "Got it! It's 2:34 AM now, and I'll remind you at 2:39 AM to check the oven."
```

### List Reminders

**Input Patterns**:
```
"what reminders do I have"
"list my reminders"
"show my reminders"
"check my reminders"
```

### Cancel Reminder

**Input Patterns**:
```
"cancel my reminder about [task]"
"cancel the [task] reminder"
"delete reminder number [N]"
"cancel the [ordinal] reminder"
```

---

## Time Commands

### Current Time

**Input Patterns**:
```
"what time is it"
"what's the time"
"tell me the time"
```

### Date Query

**Input Patterns**:
```
"what day is it"
"what's today's date"
"what is the date"
```

---

## Activity Tracking (Feature: 005-time-tracking-notes)

### Start Activity

**Input Patterns**:
```
"I'm going to [activity]"
"I'm starting [activity]"
"beginning [activity]"
```

### End Activity

**Input Patterns**:
```
"I'm done with [activity]"
"finished [activity]"
"stopping [activity]"
```

### Duration Query

**Input Patterns**:
```
"how long was I in [activity]"
"how long did [activity] take"
```

### Activity Search

**Input Patterns**:
```
"what was I doing around [time]"
"what happened between [time] and [time]"
"what did I do yesterday"
"when did I last mention [keyword]"
```

---

## Note Capture

**Input Patterns**:
```
"remember [note]"
"note that [note]"
"save a note [note]"
"add [item] to my action items"
"add [item] to my to-do list"
```

---

## General Questions

Any question not matching specific patterns is routed to the local LLM:

```
"what is the capital of France"
"explain quantum computing"
"how do I make pasta"
```

---

## Tips for Best Results

1. **Speak clearly** - Ara works best with clear pronunciation
2. **Use natural language** - Commands are designed for conversational speech
3. **Wait for feedback** - Listen for confirmation sounds before the next command
4. **Follow-up naturally** - Within 5 seconds of a Claude response, ask follow-ups without saying "ask Claude"
