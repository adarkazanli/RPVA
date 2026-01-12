# Data Model: Ara Voice Assistant

**Date**: 2026-01-12
**Branch**: `001-ara-voice-assistant`

## Overview

This document defines the core entities, their attributes, relationships, and validation rules for the Ara voice assistant.

---

## 1. Interaction

A single user query and system response pair.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique interaction identifier |
| `session_id` | UUID | Yes | Parent session reference |
| `timestamp` | DateTime | Yes | UTC timestamp of interaction start |
| `device_id` | String | Yes | Device identifier (e.g., "pi4-kitchen") |
| `wake_word_confidence` | Float | Yes | 0.0-1.0 confidence score |
| `audio_duration_ms` | Integer | Yes | Duration of user audio input |
| `transcript` | String | Yes | STT transcription result |
| `transcript_confidence` | Float | Yes | 0.0-1.0 confidence score |
| `intent` | String | Yes | Classified intent (e.g., "timer_set") |
| `intent_confidence` | Float | Yes | 0.0-1.0 confidence score |
| `entities` | JSON | No | Extracted entities (key-value pairs) |
| `response` | String | Yes | LLM-generated response text |
| `response_source` | Enum | Yes | "local_llm", "cloud_api", "system" |
| `latency_ms` | JSON | Yes | Component latencies (see below) |
| `mode` | Enum | Yes | "offline", "online_local", "online_cloud" |
| `error` | String | No | Error message if interaction failed |
| `created_at` | DateTime | Yes | Record creation timestamp |

### Latency Structure

```json
{
  "wake_word": 45,
  "stt": 412,
  "llm": 623,
  "tts": 198,
  "total": 1278
}
```

### Validation Rules

- `wake_word_confidence` must be >= 0.85 to proceed
- `transcript` must not be empty after processing
- `latency_ms.total` should be <= 6000ms (warning if exceeded)
- `response_source` must match current `mode`

### Relationships

- Belongs to one **Session**
- May have zero or more extracted **ActionItems**

---

## 2. Session

A grouping of related interactions.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique session identifier |
| `device_id` | String | Yes | Device identifier |
| `started_at` | DateTime | Yes | First interaction timestamp |
| `ended_at` | DateTime | No | Last interaction + timeout |
| `interaction_count` | Integer | Yes | Number of interactions in session |
| `mode` | Enum | Yes | Session mode (may change during session) |
| `metadata` | JSON | No | Additional session context |

### State Transitions

```
[Created] --> [Active] --> [Ended]
                 |
                 +--> [Timeout] --> [Ended]
```

- **Created**: Session starts with first wake word detection
- **Active**: Accepting new interactions
- **Timeout**: No interaction for 5 minutes
- **Ended**: Session closed (timeout or explicit end)

### Validation Rules

- `ended_at` must be >= `started_at`
- `interaction_count` must match actual interaction records

### Relationships

- Has many **Interactions**

---

## 3. Timer

A countdown timer with alert capability.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique timer identifier |
| `name` | String | No | User-assigned name (e.g., "pasta timer") |
| `duration_seconds` | Integer | Yes | Total timer duration |
| `started_at` | DateTime | Yes | Timer start timestamp |
| `expires_at` | DateTime | Yes | Calculated expiration time |
| `status` | Enum | Yes | "running", "paused", "completed", "cancelled" |
| `alert_played` | Boolean | Yes | Whether alert has been triggered |
| `created_by_interaction` | UUID | Yes | Interaction that created this timer |

### State Transitions

```
[Created] --> [Running] --> [Completed]
                  |              |
                  +--> [Paused] -+
                  |
                  +--> [Cancelled]
```

### Validation Rules

- `duration_seconds` must be > 0 and <= 86400 (24 hours)
- `expires_at` = `started_at` + `duration_seconds`
- Only "running" timers trigger alerts

### Relationships

- Created by one **Interaction**
- No direct relationship to Session (persists across sessions)

---

## 4. Reminder

A scheduled notification for a specific time.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique reminder identifier |
| `message` | String | Yes | Reminder content (e.g., "call mom") |
| `remind_at` | DateTime | Yes | When to trigger reminder |
| `recurrence` | Enum | No | "none", "daily", "weekly", "monthly" |
| `status` | Enum | Yes | "pending", "triggered", "dismissed", "cancelled" |
| `triggered_at` | DateTime | No | When reminder was actually triggered |
| `created_by_interaction` | UUID | Yes | Interaction that created this reminder |
| `created_at` | DateTime | Yes | Record creation timestamp |

### State Transitions

```
[Pending] --> [Triggered] --> [Dismissed]
     |                             |
     +-------> [Cancelled] <-------+
```

### Validation Rules

- `remind_at` must be in the future when created
- `message` must be 1-500 characters
- Recurring reminders create new instances after trigger

### Relationships

- Created by one **Interaction**
- May generate future **Reminder** instances if recurring

---

## 5. DailySummary

Aggregated statistics for a 24-hour period.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique summary identifier |
| `date` | Date | Yes | Summary date (YYYY-MM-DD) |
| `device_id` | String | Yes | Device identifier |
| `total_interactions` | Integer | Yes | Count of all interactions |
| `successful_interactions` | Integer | Yes | Count of successful interactions |
| `error_count` | Integer | Yes | Count of failed interactions |
| `avg_latency_ms` | Integer | Yes | Average total latency |
| `p95_latency_ms` | Integer | Yes | 95th percentile latency |
| `mode_breakdown` | JSON | Yes | Count per mode |
| `top_intents` | JSON | Yes | Top 10 intents with counts |
| `action_items` | JSON | Yes | Extracted action items |
| `notable_interactions` | JSON | No | Unusual or complex queries |
| `generated_at` | DateTime | Yes | When summary was generated |

### Mode Breakdown Structure

```json
{
  "offline": 45,
  "online_local": 10,
  "online_cloud": 5
}
```

### Top Intents Structure

```json
[
  {"intent": "timer_set", "count": 12},
  {"intent": "general_question", "count": 8},
  {"intent": "weather_query", "count": 5}
]
```

### Validation Rules

- `date` must not be in the future
- `total_interactions` = `successful_interactions` + `error_count`
- Only one summary per device per date

### Relationships

- Aggregates many **Interactions** from the date

---

## 6. UserPreference

User configuration settings.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique preference identifier |
| `device_id` | String | Yes | Device identifier |
| `preferred_mode` | Enum | Yes | "offline", "online_local", "online_cloud" |
| `voice_id` | String | Yes | TTS voice identifier |
| `wake_word_sensitivity` | Float | Yes | 0.0-1.0 (higher = more sensitive) |
| `logging_enabled` | Boolean | Yes | Whether to log interactions |
| `audio_feedback_enabled` | Boolean | Yes | Play beeps and chimes |
| `updated_at` | DateTime | Yes | Last modification timestamp |

### Validation Rules

- `wake_word_sensitivity` must be 0.3-0.9 (extremes cause issues)
- `voice_id` must be a valid installed voice
- One preference record per device

### Relationships

- Belongs to one device (by `device_id`)

---

## 7. ConfigProfile

Platform-specific runtime configuration.

### Attributes

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Profile name ("dev", "prod") |
| `platform` | Enum | Yes | "macos", "linux", "raspberrypi" |
| `audio_input_device` | String | Yes | Input device identifier |
| `audio_output_device` | String | Yes | Output device identifier |
| `model_acceleration` | Enum | Yes | "cpu", "metal", "cuda" |
| `mock_audio_enabled` | Boolean | Yes | Use mock audio for testing |
| `log_level` | Enum | Yes | "DEBUG", "INFO", "WARNING", "ERROR" |
| `model_paths` | JSON | Yes | Paths to model files |

### Model Paths Structure

```json
{
  "whisper": "~/.ara/models/whisper/base.en",
  "piper": "~/.ara/models/piper/en_US-lessac-medium"
}
```

### Validation Rules

- `name` must be unique
- Audio devices must exist on target platform
- `model_acceleration` must be available on platform

### Relationships

- No direct relationships (configuration entity)

---

## Entity Relationship Diagram

```
┌─────────────────┐
│     Session     │
│─────────────────│
│ id              │
│ device_id       │
│ started_at      │
│ ended_at        │
└────────┬────────┘
         │ 1
         │
         │ *
┌────────┴────────┐       ┌─────────────────┐
│   Interaction   │───────│   DailySummary  │
│─────────────────│   *   │─────────────────│
│ id              │       │ id              │
│ session_id (FK) │       │ date            │
│ transcript      │       │ device_id       │
│ response        │       │ statistics...   │
│ latency_ms      │       └─────────────────┘
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼ 0..1    ▼ 0..1
┌───────┐   ┌──────────┐
│ Timer │   │ Reminder │
│───────│   │──────────│
│ id    │   │ id       │
│ name  │   │ message  │
│ status│   │ remind_at│
└───────┘   └──────────┘
```

---

## Storage Implementation

### SQLite Schema

```sql
-- Interactions table
CREATE TABLE interactions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL,
    wake_word_confidence REAL NOT NULL,
    audio_duration_ms INTEGER NOT NULL,
    transcript TEXT NOT NULL,
    transcript_confidence REAL NOT NULL,
    intent TEXT NOT NULL,
    intent_confidence REAL NOT NULL,
    entities TEXT,  -- JSON
    response TEXT NOT NULL,
    response_source TEXT NOT NULL,
    latency_ms TEXT NOT NULL,  -- JSON
    mode TEXT NOT NULL,
    error TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Timers table
CREATE TABLE timers (
    id TEXT PRIMARY KEY,
    name TEXT,
    duration_seconds INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    alert_played INTEGER NOT NULL DEFAULT 0,
    created_by_interaction TEXT NOT NULL,
    FOREIGN KEY (created_by_interaction) REFERENCES interactions(id)
);

-- Reminders table
CREATE TABLE reminders (
    id TEXT PRIMARY KEY,
    message TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    recurrence TEXT DEFAULT 'none',
    status TEXT NOT NULL DEFAULT 'pending',
    triggered_at TEXT,
    created_by_interaction TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (created_by_interaction) REFERENCES interactions(id)
);

-- Indexes
CREATE INDEX idx_interactions_session ON interactions(session_id);
CREATE INDEX idx_interactions_timestamp ON interactions(timestamp);
CREATE INDEX idx_timers_status ON timers(status);
CREATE INDEX idx_reminders_remind_at ON reminders(remind_at);
```

### JSON Lines Format

Each line in `YYYY-MM-DD.jsonl` is a complete Interaction JSON object.
