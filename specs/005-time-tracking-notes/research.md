# Research: Enhanced Note-Taking & Time Tracking

**Feature**: 005-time-tracking-notes | **Date**: 2026-01-14

## 1. Entity Extraction Approach

### Decision: Structured JSON Prompting with Local LLM

Use the existing `OllamaLanguageModel` with a specialized system prompt that returns structured JSON containing extracted entities.

### Rationale

- **Offline-first**: Ollama runs locally, no cloud dependency
- **Existing infrastructure**: Reuses `src/ara/llm/ollama.py` without new dependencies
- **Performance**: Llama 3.2:3b can handle extraction in <2 seconds
- **Structured output**: JSON format enables reliable parsing

### Implementation

```python
EXTRACTION_PROMPT = """Extract entities from this note. Return ONLY valid JSON:
{
  "people": ["name1", "name2"],
  "topics": ["topic1", "topic2"],
  "locations": ["location1"]
}

Note: "{transcript}"
"""
```

### Alternatives Considered

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Local LLM (chosen)** | Offline, existing infra, good accuracy | Slower than regex | ✅ Selected |
| spaCy NER | Fast, accurate for standard entities | Requires new dependency, misses context | ❌ Rejected |
| Regex patterns | Very fast | Poor accuracy for natural speech | ❌ Rejected |
| Cloud NLP (GPT-4) | Highest accuracy | Requires internet, adds latency, cost | ❌ Rejected |

### Performance Target

- Entity extraction: <2 seconds (within existing 4s LLM budget)
- Accuracy: 80% for typical conversational inputs

---

## 2. Auto-Categorization Strategy

### Decision: Keyword-First with LLM Fallback

Two-stage approach:
1. **Fast path**: Keyword matching for obvious categories (<10ms)
2. **Slow path**: LLM classification for ambiguous cases (<1.5s)

### Rationale

- Most inputs have clear category signals (workout→health, meeting→work)
- Keyword matching handles 70-80% of cases instantly
- LLM fallback handles edge cases without sacrificing accuracy

### Implementation

```python
CATEGORY_KEYWORDS = {
    "health": ["workout", "exercise", "gym", "run", "yoga", "meditation", "doctor", "health"],
    "work": ["meeting", "call", "project", "deadline", "client", "sprint", "standup", "work"],
    "errands": ["groceries", "shopping", "pickup", "drop off", "errand", "pharmacy", "bank"],
    "personal": ["family", "friend", "dinner", "lunch", "movie", "game", "hobby"],
}

def categorize(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    # Fallback to LLM
    return llm_categorize(text)
```

### Categories (Fixed)

| Category | Examples |
|----------|----------|
| `work` | meetings, calls, projects, deadlines |
| `personal` | family time, hobbies, socializing |
| `health` | exercise, medical, meditation |
| `errands` | shopping, appointments, chores |
| `uncategorized` | fallback when confidence is low |

### Performance Target

- Keyword path: <10ms
- LLM fallback: <1.5s
- Overall accuracy: 85% for clear-cut categories

---

## 3. Activity Tracking Patterns

### Decision: Intent-Based Detection in Router

Detect activity start/stop via intent classification in the existing router, not as a separate system.

### Rationale

- Integrates with existing `Intent` enum in `src/ara/router/intent.py`
- Leverages existing orchestrator pattern
- Single source of truth for command interpretation

### New Intents

```python
class Intent(Enum):
    # Existing intents...
    ACTIVITY_START = "activity_start"      # "starting X", "beginning X"
    ACTIVITY_STOP = "activity_stop"        # "done with X", "finished X"
    NOTE_CAPTURE = "note_capture"          # "note that...", "remember..."
    DIGEST_DAILY = "digest_daily"          # "how did I spend my time today"
    DIGEST_WEEKLY = "digest_weekly"        # "weekly summary", "this week"
```

### Pattern Examples

| Trigger Phrases | Intent | Extracted Entity |
|-----------------|--------|------------------|
| "starting my workout" | ACTIVITY_START | activity="workout" |
| "beginning work on the report" | ACTIVITY_START | activity="work on the report" |
| "done with lunch" | ACTIVITY_STOP | activity="lunch" |
| "finished coding" | ACTIVITY_STOP | activity="coding" |

### Edge Cases

- **No matching activity**: Create completed activity, estimate duration or prompt
- **Overlapping activities**: Auto-close previous, start new (single active)
- **Timeout**: Auto-close after 4 hours (configurable)

---

## 4. Digest Generation Approach

### Decision: MongoDB Aggregation + LLM Summary

1. **Data retrieval**: MongoDB aggregation pipeline for time-range filtering and category grouping
2. **Summarization**: LLM generates natural language summary from aggregated data

### Rationale

- MongoDB aggregation is efficient for date-range queries
- LLM makes the summary conversational and natural
- Separation allows caching aggregated data

### Implementation Flow

```
User: "How did I spend my time today?"
  ↓
1. Query: db.activities.aggregate([
     { $match: { date: today } },
     { $group: { _id: "$category", total_minutes: { $sum: "$duration" } } }
   ])
  ↓
2. Result: { work: 180, health: 60, errands: 30 }
  ↓
3. LLM Prompt: "Summarize this time breakdown naturally: work=3h, health=1h, errands=30m"
  ↓
4. Response: "Today you spent 3 hours on work, 1 hour on health, and 30 minutes on errands."
```

### Performance Target

- Aggregation query: <500ms
- LLM summarization: <2s
- Total digest: <3 seconds

---

## 5. Storage Design

### Decision: Two New MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `notes` | Voice notes with extracted entities |
| `activities` | Time-tracked activities with duration |

### Rationale

- Separates concerns (notes vs time tracking)
- Enables efficient querying per use case
- Follows existing MongoDB patterns in `src/ara/storage/`

### Indexes

```python
# notes collection
db.notes.create_index([("timestamp", -1)])
db.notes.create_index([("people", 1)])
db.notes.create_index([("topics", 1)])
db.notes.create_index([("category", 1)])

# activities collection
db.activities.create_index([("start_time", -1)])
db.activities.create_index([("category", 1)])
db.activities.create_index([("status", 1)])  # "active" | "completed"
```

---

## Summary

| Component | Approach | Performance |
|-----------|----------|-------------|
| Entity extraction | Ollama JSON prompting | <2s |
| Categorization | Keywords + LLM fallback | <10ms / <1.5s |
| Activity detection | Intent-based router | <100ms |
| Digest generation | MongoDB agg + LLM | <3s |
| Storage | Two MongoDB collections | N/A |

All approaches comply with constitution principles (offline-first, performance budgets, modularity).
