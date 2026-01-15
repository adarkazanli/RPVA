# Quickstart: Enhanced Note-Taking & Time Tracking

**Feature**: 005-time-tracking-notes | **Date**: 2026-01-14

## Voice Commands

### Capturing Notes

| Say This | What Happens |
|----------|--------------|
| "Note that I talked to Sarah about the budget" | Captures note, extracts person="Sarah", topic="budget" |
| "Remember meeting with John at Starbucks" | Captures note, extracts person="John", location="Starbucks" |
| "I just discussed the Q1 roadmap with the team" | Captures note, extracts topic="Q1 roadmap", people="team" |

### Starting Activities

| Say This | What Happens |
|----------|--------------|
| "Starting my workout" | Starts tracking "workout" (category: health) |
| "Beginning work on the report" | Starts tracking "work on the report" (category: work) |
| "I'm going to meditate" | Starts tracking "meditate" (category: health) |

### Stopping Activities

| Say This | What Happens |
|----------|--------------|
| "Done with my workout" | Stops "workout", reports duration |
| "Finished coding" | Stops "coding", reports duration |
| "Completed the errands" | Stops "errands", reports duration |

### Querying Notes

| Say This | Response |
|----------|----------|
| "What did I discuss with Sarah?" | Lists all notes mentioning Sarah |
| "What meetings did I have today?" | Lists today's work-category notes |
| "What have I been working on?" | Lists recent work activities |

### Daily Digest

| Say This | Response |
|----------|----------|
| "How did I spend my time today?" | "Today you spent 3 hours on work, 1 hour on health, and 30 minutes on errands." |
| "What did I do this morning?" | Filters to AM activities |
| "Summarize my day" | Same as "how did I spend my time today" |

### Weekly Insights

| Say This | Response |
|----------|----------|
| "How did I spend my time this week?" | Weekly breakdown by category with totals |
| "What patterns do you see?" | "You spend most of your productive hours in the morning. Wednesdays are your busiest work days." |
| "Am I spending enough time on health?" | Compares health time to recommendations |

---

## Example Conversations

### Scenario 1: Capturing a Meeting Note

```
User: "Hey Ara, note that I had a meeting with Sarah and John about the Q1 budget at the downtown office"

Ara: "Got it! Noted your meeting about Q1 budget."

[Stored note with:]
- people: ["Sarah", "John"]
- topics: ["Q1 budget"]
- locations: ["downtown office"]
- category: "work"
```

### Scenario 2: Tracking a Workout

```
User: "Starting my workout"

Ara: "Started tracking workout. Get after it!"

[30 minutes later...]

User: "Done with my workout"

Ara: "Nice! Workout completed - 30 minutes."

[Activity stored with duration_minutes: 30, category: "health"]
```

### Scenario 3: Activity Overlap

```
User: "Starting coding"

Ara: "Started tracking coding."

[2 hours later...]

User: "Starting lunch"

Ara: "Stopped coding (2 hours). Started tracking lunch."

[Coding auto-closed, lunch started]
```

### Scenario 4: Daily Digest

```
User: "How did I spend my time today?"

Ara: "Today you spent 4 hours on work, including coding and meetings.
      You also did 45 minutes of exercise and 30 minutes of errands.
      Total: 5 hours 15 minutes tracked."
```

### Scenario 5: Querying by Person

```
User: "What did I discuss with Sarah?"

Ara: "You discussed Q1 budget with Sarah yesterday, and project timeline on Monday."
```

---

## Test Scenarios

### Test 1: Entity Extraction Accuracy

**Setup**: Capture 10 notes with known entities
**Input**: "Meeting with Dr. Smith about the annual checkup at the clinic"
**Expected**:
- people: ["Dr. Smith"]
- topics: ["annual checkup"]
- locations: ["clinic"]
- category: "health"
**Verify**: 80% extraction accuracy across 10 samples

### Test 2: Activity Duration Tracking

**Setup**: Start activity, wait 5 minutes, stop
**Steps**:
1. Say "Starting test activity"
2. Wait exactly 5 minutes
3. Say "Done with test activity"
**Expected**: duration_minutes = 5 (±1 minute)

### Test 3: Auto-Close on New Activity

**Setup**: Start activity A, then start activity B without closing A
**Steps**:
1. Say "Starting reading"
2. Wait 10 minutes
3. Say "Starting cooking"
**Expected**:
- "reading" auto-closed with ~10 minute duration
- "cooking" now active

### Test 4: Daily Digest Generation

**Setup**: Track 3+ activities of different categories
**Steps**:
1. Track: workout (health, 30min), meeting (work, 60min), groceries (errands, 20min)
2. Say "How did I spend my time today?"
**Expected**: Breakdown showing all three categories with correct durations
**Performance**: Response in <3 seconds

### Test 5: Timeout Auto-Close

**Setup**: Start activity, wait beyond timeout
**Steps**:
1. Say "Starting long task"
2. Simulate 4+ hours passing
3. Trigger timeout check
**Expected**: Activity auto-closed, `auto_closed: true`

---

## Error Handling

| Scenario | User Says | Response |
|----------|-----------|----------|
| No active activity | "Done with workout" | "I don't have an active workout. Did you forget to start it?" |
| No data for digest | "How did I spend my time today?" | "I don't have any activities tracked for today yet." |
| Ambiguous person | "What did I discuss with John?" (multiple Johns) | Shows all matches; future: "I found notes with John Smith and John Doe. Which one?" |
| Empty query result | "What did I discuss with Sarah?" (no matches) | "I don't have any notes mentioning Sarah." |
