# Data Model: MongoDB Data Store for Voice Agent

**Date**: 2026-01-14
**Feature**: [spec.md](spec.md)

## Overview

This document defines the MongoDB document schemas for persistent storage of voice agent interactions, events, and activities. The schema design supports time-based queries, event pairing, and historical data access.

---

## Collections

### 1. `interactions`

Stores all voice agent interactions with timestamps and metadata.

**Schema**:
```json
{
  "_id": "ObjectId",
  "session_id": "UUID string",
  "timestamp": "ISODate",
  "device_id": "string",

  "input": {
    "transcript": "string",
    "confidence": "float (0-1)",
    "audio_duration_ms": "integer"
  },

  "intent": {
    "type": "string (enum)",
    "confidence": "float (0-1)",
    "entities": {
      "duration": "integer (optional)",
      "time": "string (optional)",
      "subject": "string (optional)"
    }
  },

  "response": {
    "text": "string",
    "source": "string (local_llm|cloud_api|system)"
  },

  "latency_ms": {
    "stt": "integer",
    "llm": "integer",
    "tts": "integer",
    "total": "integer"
  },

  "events_extracted": ["ObjectId (ref to events)"],
  "created_at": "ISODate"
}
```

**Indexes**:
```python
# Primary query indexes
interactions.create_index([("timestamp", -1)])
interactions.create_index([("session_id", 1)])
interactions.create_index([("device_id", 1), ("timestamp", -1)])

# Full-text search on transcript
interactions.create_index([("input.transcript", "text")])
```

**Validation Rules**:
- `timestamp` required, must be valid ISO date
- `input.transcript` required, non-empty string
- `intent.type` required, from defined enum
- `latency_ms.total` >= sum of component latencies

---

### 2. `events`

Stores meaningful events extracted from interactions.

**Schema**:
```json
{
  "_id": "ObjectId",
  "interaction_id": "ObjectId (ref to interactions)",
  "timestamp": "ISODate",

  "type": "string (enum: activity_start|activity_end|note|reminder|query)",
  "context": "string (description of event)",
  "context_embedding": "[float array, 300 dimensions] (optional)",

  "entities": {
    "location": "string (optional)",
    "person": "string (optional)",
    "object": "string (optional)"
  },

  "linked_event_id": "ObjectId (optional, for paired events)",
  "activity_id": "ObjectId (optional, ref to activities)",

  "metadata": {
    "source_text": "string (original transcript)",
    "extraction_confidence": "float (0-1)"
  },

  "created_at": "ISODate"
}
```

**Event Types**:
| Type | Description | Example |
|------|-------------|---------|
| `activity_start` | Begin of trackable activity | "I'm going to the gym" |
| `activity_end` | End of trackable activity | "I'm done with my workout" |
| `note` | General information to remember | "I parked on level 3" |
| `reminder` | Time-sensitive reminder | "Remind me to call mom" |
| `query` | User query about past events | "How long was I in the shower?" |

**Indexes**:
```python
# Time-based queries
events.create_index([("timestamp", -1)])
events.create_index([("type", 1), ("timestamp", -1)])

# Activity pairing
events.create_index([("context", 1), ("timestamp", -1)])
events.create_index([("linked_event_id", 1)])
events.create_index([("activity_id", 1)])
```

---

### 3. `activities`

Stores paired activity start/end events with duration.

**Schema**:
```json
{
  "_id": "ObjectId",
  "name": "string (normalized activity name)",
  "status": "string (enum: in_progress|completed|abandoned)",

  "start_event_id": "ObjectId (ref to events)",
  "end_event_id": "ObjectId (optional, ref to events)",

  "start_time": "ISODate",
  "end_time": "ISODate (optional)",
  "duration_ms": "integer (optional, calculated)",

  "context": {
    "start_text": "string (original start transcript)",
    "end_text": "string (optional, original end transcript)"
  },

  "pairing_score": "float (0-1, semantic + temporal score)",

  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

**Activity Status Transitions**:
```
in_progress → completed (end event matched)
in_progress → abandoned (timeout or manual cancellation)
```

**Indexes**:
```python
# Status queries
activities.create_index([("status", 1), ("start_time", -1)])

# Duration queries
activities.create_index([("name", 1), ("start_time", -1)])
activities.create_index([("end_time", -1)])
```

---

### 4. `time_queries`

Stores user queries about time-based information.

**Schema**:
```json
{
  "_id": "ObjectId",
  "interaction_id": "ObjectId (ref to interactions)",
  "timestamp": "ISODate",

  "query_type": "string (enum: duration|range_search|point_search)",
  "parameters": {
    "event_1": "string (for duration queries)",
    "event_2": "string (for duration queries)",
    "time_point": "ISODate (for point_search)",
    "time_range": {
      "start": "ISODate",
      "end": "ISODate"
    }
  },

  "result": {
    "success": "boolean",
    "duration_ms": "integer (optional)",
    "events_found": ["ObjectId"],
    "activities_found": ["ObjectId"],
    "response_text": "string"
  },

  "created_at": "ISODate"
}
```

**Query Types**:
| Type | Description | Example Question |
|------|-------------|------------------|
| `duration` | Time between two events | "How long was I in the shower?" |
| `range_search` | Events within time range | "What happened between 9 and noon?" |
| `point_search` | Events around a time point | "What was I doing around 10 AM?" |

---

## Entity Relationships

```
interactions ──┬── 1:N ──► events
               │
               └── 1:1 ──► time_queries

events ──┬── N:1 ──► interactions
         │
         ├── 1:1 ──► events (linked_event_id)
         │
         └── N:1 ──► activities

activities ──┬── 1:1 ──► events (start_event)
             │
             └── 1:1 ──► events (end_event)
```

---

## Data Archiving Strategy

Per FR-010 and FR-011, older data is automatically archived:

### Archive Trigger
- When collection size exceeds threshold (configurable, default 1GB)
- Data older than 90 days moved to archive

### Archive Collection Schema
```json
{
  "_id": "ObjectId",
  "original_collection": "string (interactions|events|activities)",
  "original_id": "ObjectId",
  "archived_at": "ISODate",
  "data": "object (original document)"
}
```

### Archive Index
```python
archive.create_index([("original_collection", 1), ("archived_at", -1)])
```

### Query Behavior
- Recent data: Primary collections (fast)
- Archived data: Archive collection with user notification

---

## Validation Rules Summary

| Collection | Field | Rule |
|------------|-------|------|
| interactions | timestamp | Required, valid ISODate |
| interactions | input.transcript | Required, non-empty |
| interactions | intent.type | Required, valid enum |
| events | type | Required, valid enum |
| events | timestamp | Required, valid ISODate |
| events | context | Required, non-empty |
| activities | status | Required, valid enum |
| activities | start_event_id | Required, valid ObjectId |
| activities | start_time | Required, valid ISODate |

---

## Sample Documents

### Interaction Example
```json
{
  "_id": "ObjectId('...')",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-01-14T10:30:00Z",
  "device_id": "pi-living-room",
  "input": {
    "transcript": "I'm going to take a shower",
    "confidence": 0.95,
    "audio_duration_ms": 2500
  },
  "intent": {
    "type": "activity_log",
    "confidence": 0.88,
    "entities": {
      "subject": "shower"
    }
  },
  "response": {
    "text": "Got it, I'll note that you started your shower at 10:30 AM.",
    "source": "local_llm"
  },
  "latency_ms": {
    "stt": 850,
    "llm": 1200,
    "tts": 320,
    "total": 2370
  },
  "events_extracted": ["ObjectId('event1...')"],
  "created_at": "2026-01-14T10:30:02Z"
}
```

### Event Example (Activity Start)
```json
{
  "_id": "ObjectId('event1...')",
  "interaction_id": "ObjectId('...')",
  "timestamp": "2026-01-14T10:30:00Z",
  "type": "activity_start",
  "context": "shower",
  "entities": {
    "location": null,
    "person": null,
    "object": "shower"
  },
  "linked_event_id": null,
  "activity_id": "ObjectId('activity1...')",
  "metadata": {
    "source_text": "I'm going to take a shower",
    "extraction_confidence": 0.92
  },
  "created_at": "2026-01-14T10:30:02Z"
}
```

### Activity Example (Completed)
```json
{
  "_id": "ObjectId('activity1...')",
  "name": "shower",
  "status": "completed",
  "start_event_id": "ObjectId('event1...')",
  "end_event_id": "ObjectId('event2...')",
  "start_time": "2026-01-14T10:30:00Z",
  "end_time": "2026-01-14T10:45:00Z",
  "duration_ms": 900000,
  "context": {
    "start_text": "I'm going to take a shower",
    "end_text": "I'm done with my shower"
  },
  "pairing_score": 0.87,
  "created_at": "2026-01-14T10:30:02Z",
  "updated_at": "2026-01-14T10:45:03Z"
}
```

---

## Migration Notes

### From SQLite (existing `storage.py`)

The existing `InteractionStorage` class stores to SQLite. Migration steps:

1. Export existing interactions using `get_by_date_range()`
2. Transform to new MongoDB schema
3. Insert into MongoDB collections
4. Update `InteractionLogger` to use MongoDB backend

### Backward Compatibility

- Keep SQLite as fallback when MongoDB unavailable
- Storage abstraction layer supports both backends
- No data loss during transition period
