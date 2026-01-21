# Data Model: Claude Query Mode

**Feature**: 009-claude-query-mode
**Date**: 2026-01-21

## Entities

### ClaudeQuery

Represents a single user query sent to Claude.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | Yes | MongoDB document ID |
| `type` | string | Yes | Always `"claude_query"` for filtering |
| `session_id` | string | Yes | UUID linking queries in same conversation |
| `utterance` | string | Yes | Original user speech transcription |
| `is_followup` | boolean | Yes | True if query was in follow-up window |
| `timestamp` | datetime | Yes | When query was received |
| `created_at` | datetime | Yes | When document was created |

**Indexes**:
- `timestamp` (descending) - for time-based queries
- `session_id` - for conversation grouping
- `type` - for filtering Claude queries

### ClaudeResponse

Represents Claude's response to a query.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `_id` | ObjectId | Yes | MongoDB document ID |
| `type` | string | Yes | Always `"claude_response"` for filtering |
| `query_id` | ObjectId | Yes | Reference to ClaudeQuery |
| `session_id` | string | Yes | Session reference for convenience |
| `text` | string | Yes | Full response text from Claude |
| `tokens_used` | integer | Yes | Total tokens (input + output) |
| `model` | string | Yes | Claude model used (e.g., "claude-3-opus") |
| `latency_ms` | integer | Yes | API response time in milliseconds |
| `timestamp` | datetime | Yes | When response was received |
| `created_at` | datetime | Yes | When document was created |

**Indexes**:
- `timestamp` (descending) - for time-based queries
- `query_id` - for linking to query
- `session_id` - for conversation grouping
- `type` - for filtering Claude responses

### ClaudeSession (In-Memory)

Represents an active conversation session with Claude. Not persisted to MongoDB.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | UUID for this session |
| `messages` | list[Message] | Yes | Conversation history |
| `created_at` | datetime | Yes | When session started |
| `last_activity` | datetime | Yes | Last query/response time |

**Message Structure**:
```python
@dataclass
class Message:
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
```

**Session Lifecycle**:
- Created: On first "ask Claude" query
- Updated: On each query/response
- Cleared: On "new conversation" command or explicit reset

### ClaudeConfig

Configuration for Claude integration. Stored in config file or environment.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `api_key` | string | Yes | - | Anthropic API key (from env) |
| `model` | string | No | `"claude-sonnet-4-20250514"` | Claude model to use |
| `max_tokens` | integer | No | `500` | Max response tokens (~150 words) |
| `temperature` | float | No | `0.7` | Response creativity |
| `timeout_seconds` | integer | No | `30` | API timeout |

## Relationships

```
ClaudeSession (in-memory)
    │
    ├── contains → Message[]
    │
    └── generates → ClaudeQuery (persisted)
                        │
                        └── has → ClaudeResponse (persisted)
```

## State Transitions

### ClaudeSession States

```
[No Session] ──"ask Claude X"──► [Active]
                                    │
            ┌───────────────────────┤
            │                       │
            ▼                       │
    [Follow-up Window]              │
      (5 seconds)                   │
            │                       │
    ┌───────┴───────┐               │
    │               │               │
    ▼               ▼               │
[Continue]    [Window Closed]       │
    │               │               │
    └───────────────┴───────────────┤
                                    │
            "new conversation" ─────┘
                    │
                    ▼
              [No Session]
```

## Validation Rules

### ClaudeQuery
- `utterance` must not be empty
- `session_id` must be valid UUID format
- `timestamp` must be in the past

### ClaudeResponse
- `query_id` must reference existing ClaudeQuery
- `text` must not be empty
- `tokens_used` must be > 0
- `latency_ms` must be >= 0

### ClaudeSession
- `messages` list capped at 20 entries (FIFO eviction)
- Session auto-persists queries/responses to MongoDB

## Query Patterns

### Time-Based Retrieval (FR-016)

```python
# Today's queries
def get_queries_today() -> list[ClaudeQuery]:
    start = datetime.now().replace(hour=0, minute=0, second=0)
    return collection.find({
        "type": "claude_query",
        "timestamp": {"$gte": start}
    }).sort("timestamp", DESCENDING)

# This week's queries
def get_queries_this_week() -> list[ClaudeQuery]:
    start = datetime.now() - timedelta(days=7)
    return collection.find({
        "type": "claude_query",
        "timestamp": {"$gte": start}
    }).sort("timestamp", DESCENDING)

# This month's queries
def get_queries_this_month() -> list[ClaudeQuery]:
    start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    return collection.find({
        "type": "claude_query",
        "timestamp": {"$gte": start}
    }).sort("timestamp", DESCENDING)
```

### Summarization Query (FR-017)

```python
# Get queries with responses for summarization
def get_conversations_for_period(start: datetime, end: datetime):
    queries = collection.find({
        "type": "claude_query",
        "timestamp": {"$gte": start, "$lte": end}
    })

    result = []
    for query in queries:
        response = collection.find_one({
            "type": "claude_response",
            "query_id": query["_id"]
        })
        result.append({"query": query, "response": response})

    return result
```

## Migration Notes

- New collection `claude_queries` - no migration needed
- Existing `interactions` collection unchanged
- Backward compatible with existing Ara data
