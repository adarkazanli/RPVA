# Quickstart: Smarter Query Routing

## Overview

This feature improves query routing reliability by intelligently directing queries to the most appropriate data source:

- **Personal queries** → MongoDB (prevents LLM hallucination of personal data)
- **Factual queries** → Web search (prevents LLM guessing at verifiable facts)
- **General knowledge** → LLM (fast responses for static knowledge)

## How It Works

### Query Classification Flow

```
User: "When did I last exercise?"
                │
                ▼
        ┌─────────────────┐
        │ QueryRouter     │
        │ classify()      │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
Personal?    Factual?    General?
    │            │            │
    ▼            ▼            ▼
 MongoDB      Tavily        LLM
```

### Example Queries and Routing

| Query | Detected Type | Routed To |
|-------|---------------|-----------|
| "When did I last exercise?" | PERSONAL_DATA | MongoDB |
| "What meetings did I have?" | PERSONAL_DATA | MongoDB |
| "What's the weather in Austin?" | FACTUAL_CURRENT | Web Search |
| "How far is Dallas from here?" | FACTUAL_CURRENT | Web Search |
| "What's the capital of France?" | GENERAL_KNOWLEDGE | LLM |
| "How do I make scrambled eggs?" | GENERAL_KNOWLEDGE | LLM |

## Usage

### For Users

No changes to voice commands. The system automatically routes queries:

```
You: "Ara, when did I last go to the gym?"
Ara: "Your last gym visit was yesterday at 3:45 PM for 45 minutes."
     (Answer from MongoDB, not hallucinated)

You: "Ara, what's the weather like?"
Ara: "It's 72°F and sunny in Austin right now."
     (Answer from web search, not guessed)

You: "Ara, what does serendipity mean?"
Ara: "Serendipity means finding something good without looking for it."
     (Answer from LLM, appropriate for definitions)
```

### For Developers

```python
from ara.router.query_router import QueryRouter, QueryType, DataSource

router = QueryRouter()

# Classify a query
decision = router.classify("When did I last exercise?")
print(decision.query_type)      # QueryType.PERSONAL_DATA
print(decision.primary_source)  # DataSource.DATABASE
print(decision.fallback_source) # None (don't hallucinate personal data)

# Check query type directly
router.is_personal_query("my workout")  # True
router.is_factual_query("weather in Austin")  # True
```

## Key Behaviors

### Personal Queries

- **Always** check MongoDB first
- **Never** fall back to LLM (prevents hallucination)
- Return "I don't have any records of that" if not found

### Factual Queries

- **Always** try web search first
- Fall back to LLM **with caveat** ("I couldn't verify online, but...")
- Prevents LLM from guessing distances, weather, prices

### General Knowledge Queries

- Route directly to LLM
- Fast response for static knowledge
- No external lookups needed

## Testing

Run routing tests:

```bash
PYTHONPATH=src pytest tests/unit/test_query_router.py -v
PYTHONPATH=src pytest tests/integration/test_routing_flow.py -v
```

## Configuration

Query indicators are defined in `src/ara/router/query_router.py`:

```python
PERSONAL_INDICATORS = {
    "pronouns": ["I", "me", "my", "mine"],
    "patterns": [r"when did I", r"what did I", ...],
}

FACTUAL_INDICATORS = {
    "weather": ["weather", "temperature", ...],
    "prices": ["price", "cost", "stock", ...],
}
```

## Troubleshooting

### Query routed to wrong source?

1. Check if query matches expected indicators
2. Add missing patterns to `PERSONAL_INDICATORS` or `FACTUAL_INDICATORS`
3. Run tests to verify fix doesn't break other queries

### "I don't have any records" for data that exists?

1. Verify MongoDB is connected
2. Check if data is in expected collection (interactions/activities/events)
3. Verify query matches the search pattern in MongoDB
