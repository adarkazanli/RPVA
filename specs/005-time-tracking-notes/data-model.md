# Data Model: Enhanced Note-Taking & Time Tracking

**Feature**: 005-time-tracking-notes | **Date**: 2026-01-14

## Entities

### Note

A captured voice entry with extracted context.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | ObjectId | Yes | MongoDB document ID |
| `timestamp` | datetime | Yes | When the note was captured |
| `transcript` | str | Yes | Raw voice transcript |
| `people` | list[str] | No | Extracted person names |
| `topics` | list[str] | No | Extracted subject matter |
| `locations` | list[str] | No | Extracted place references |
| `category` | Category | Yes | Auto-assigned category |
| `activity_id` | ObjectId | No | Associated activity (if any) |
| `user_id` | str | Yes | User identifier |

**Validation Rules**:
- `transcript` must be non-empty
- `category` must be a valid Category enum value
- `timestamp` defaults to current UTC time

**Example**:
```json
{
  "_id": "ObjectId(...)",
  "timestamp": "2026-01-14T10:30:00Z",
  "transcript": "Meeting with Sarah about Q1 budget at the downtown office",
  "people": ["Sarah"],
  "topics": ["Q1 budget"],
  "locations": ["downtown office"],
  "category": "work",
  "activity_id": null,
  "user_id": "default"
}
```

---

### Activity

A time-tracked activity with duration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | ObjectId | Yes | MongoDB document ID |
| `name` | str | Yes | Activity name (e.g., "workout") |
| `start_time` | datetime | Yes | When activity started |
| `end_time` | datetime | No | When activity ended (null if active) |
| `duration_minutes` | int | No | Calculated duration (null if active) |
| `category` | Category | Yes | Auto-assigned category |
| `status` | ActivityStatus | Yes | "active" or "completed" |
| `auto_closed` | bool | No | True if closed by timeout |
| `user_id` | str | Yes | User identifier |

**Validation Rules**:
- `name` must be non-empty
- `end_time` must be >= `start_time` when set
- `duration_minutes` = (end_time - start_time) in minutes
- Only one activity can have `status="active"` per user

**State Transitions**:
```
[Created] --> status="active", end_time=null
    |
    v (user says "done" OR timeout OR new activity starts)
[Completed] --> status="completed", end_time=now, duration_minutes=calculated
```

**Example**:
```json
{
  "_id": "ObjectId(...)",
  "name": "workout",
  "start_time": "2026-01-14T07:00:00Z",
  "end_time": "2026-01-14T07:45:00Z",
  "duration_minutes": 45,
  "category": "health",
  "status": "completed",
  "auto_closed": false,
  "user_id": "default"
}
```

---

### Category (Enum)

Fixed classification for notes and activities.

| Value | Description | Keywords |
|-------|-------------|----------|
| `work` | Professional tasks | meeting, call, project, deadline |
| `personal` | Personal time | family, friend, hobby |
| `health` | Health & fitness | workout, exercise, doctor |
| `errands` | Tasks & chores | groceries, shopping, errand |
| `uncategorized` | Default fallback | (no match) |

**Note**: Categories are fixed by design. Custom categories are out of scope for this feature.

---

### ActivityStatus (Enum)

| Value | Description |
|-------|-------------|
| `active` | Activity in progress |
| `completed` | Activity finished |

---

## Relationships

```
┌─────────────┐          ┌─────────────┐
│    Note     │          │  Activity   │
├─────────────┤          ├─────────────┤
│ activity_id │──────────│ id          │
│ category    │          │ category    │
│ user_id     │          │ user_id     │
└─────────────┘          └─────────────┘
       │                        │
       │                        │
       ▼                        ▼
┌─────────────┐          ┌─────────────┐
│  Category   │          │ActivityStatus│
│   (enum)    │          │   (enum)    │
└─────────────┘          └─────────────┘
```

- A **Note** can optionally reference an **Activity** (notes taken during an activity)
- Both **Note** and **Activity** have a **Category**
- **Activity** has an **ActivityStatus** for tracking state

---

## MongoDB Collections

### `notes` Collection

```javascript
db.createCollection("notes", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["timestamp", "transcript", "category", "user_id"],
      properties: {
        timestamp: { bsonType: "date" },
        transcript: { bsonType: "string", minLength: 1 },
        people: { bsonType: "array", items: { bsonType: "string" } },
        topics: { bsonType: "array", items: { bsonType: "string" } },
        locations: { bsonType: "array", items: { bsonType: "string" } },
        category: { enum: ["work", "personal", "health", "errands", "uncategorized"] },
        activity_id: { bsonType: ["objectId", "null"] },
        user_id: { bsonType: "string" }
      }
    }
  }
})
```

**Indexes**:
- `{ timestamp: -1 }` - Query by date
- `{ people: 1 }` - Query by person
- `{ topics: 1 }` - Query by topic
- `{ category: 1, timestamp: -1 }` - Category + date queries

### `activities` Collection

```javascript
db.createCollection("activities", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "start_time", "category", "status", "user_id"],
      properties: {
        name: { bsonType: "string", minLength: 1 },
        start_time: { bsonType: "date" },
        end_time: { bsonType: ["date", "null"] },
        duration_minutes: { bsonType: ["int", "null"], minimum: 0 },
        category: { enum: ["work", "personal", "health", "errands", "uncategorized"] },
        status: { enum: ["active", "completed"] },
        auto_closed: { bsonType: "bool" },
        user_id: { bsonType: "string" }
      }
    }
  }
})
```

**Indexes**:
- `{ start_time: -1 }` - Query by date
- `{ status: 1, user_id: 1 }` - Find active activity
- `{ category: 1, start_time: -1 }` - Category aggregations

---

## Python Models

Located in: `src/ara/notes/models.py` and `src/ara/activities/models.py`

```python
# src/ara/notes/models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class Category(Enum):
    WORK = "work"
    PERSONAL = "personal"
    HEALTH = "health"
    ERRANDS = "errands"
    UNCATEGORIZED = "uncategorized"

@dataclass
class Note:
    transcript: str
    category: Category
    timestamp: datetime = field(default_factory=datetime.utcnow)
    people: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    activity_id: str | None = None
    user_id: str = "default"
    id: str | None = None
```

```python
# src/ara/activities/models.py
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class ActivityStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

@dataclass
class Activity:
    name: str
    category: Category
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    duration_minutes: int | None = None
    status: ActivityStatus = ActivityStatus.ACTIVE
    auto_closed: bool = False
    user_id: str = "default"
    id: str | None = None
```
