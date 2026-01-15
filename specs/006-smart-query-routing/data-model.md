# Data Model: Smarter Query Routing

**Feature**: 006-smart-query-routing
**Date**: 2026-01-14

## Entities

### QueryType (Enum)

Classification of incoming query based on data source requirements.

| Value | Description | Data Source |
|-------|-------------|-------------|
| `PERSONAL_DATA` | Query about user's history, activities, notes | MongoDB |
| `FACTUAL_CURRENT` | Time-sensitive or verifiable facts | Web Search |
| `GENERAL_KNOWLEDGE` | Static knowledge, definitions, how-to | LLM |
| `AMBIGUOUS` | Cannot determine type with confidence | Context-dependent |

### DataSource (Enum)

Available sources for answering queries.

| Value | Description | Availability |
|-------|-------------|--------------|
| `DATABASE` | MongoDB interactions/activities/events | Offline capable |
| `WEB_SEARCH` | Tavily web search | Online required |
| `LLM` | Ollama local LLM | Offline capable |

### RoutingDecision (Dataclass)

The result of query classification with routing information.

| Field | Type | Description |
|-------|------|-------------|
| `query_type` | `QueryType` | Classified type of query |
| `primary_source` | `DataSource` | First source to try |
| `fallback_source` | `DataSource | None` | Source to try if primary fails |
| `confidence` | `float` | Confidence in classification (0.0-1.0) |
| `indicators_matched` | `list[str]` | Keywords/patterns that matched |
| `should_verify` | `bool` | Whether to verify with another source |

### QueryIndicators (Configuration)

Patterns and keywords for classifying query types.

```python
PERSONAL_INDICATORS = {
    "pronouns": ["I", "me", "my", "mine", "I'm", "I've", "I'd"],
    "patterns": [
        r"when did I",
        r"what did I",
        r"did I mention",
        r"how long was I",
        r"my \w+",
        r"have I",
        r"was I",
    ],
    "time_refs": ["last time", "yesterday", "this week", "recently", "earlier"],
}

FACTUAL_INDICATORS = {
    "weather": ["weather", "temperature", "forecast", "rain", "sunny", "cloudy"],
    "prices": ["price", "cost", "stock", "worth", "value"],
    "news": ["news", "headlines", "current events", "latest"],
    "distance": ["how far", "distance", "directions", "drive to", "miles", "kilometers"],
    "time_sensitive": ["right now", "today", "current", "latest", "live"],
    "sports": ["score", "who won", "game", "match"],
}

GENERAL_INDICATORS = {
    "definitions": ["what is", "what does", "define", "meaning of"],
    "static_facts": ["capital of", "invented", "who wrote", "who created"],
    "how_to": ["how do I", "how to", "explain", "tell me about"],
    "math": ["calculate", "plus", "minus", "percent", "divided"],
}
```

## Relationships

```
Query (input text)
    │
    ▼
QueryRouter.classify()
    │
    ▼
RoutingDecision
    │
    ├─► query_type: PERSONAL_DATA
    │       └─► primary_source: DATABASE
    │           fallback_source: None (don't hallucinate)
    │
    ├─► query_type: FACTUAL_CURRENT
    │       └─► primary_source: WEB_SEARCH
    │           fallback_source: LLM (with caveat)
    │
    └─► query_type: GENERAL_KNOWLEDGE
            └─► primary_source: LLM
                fallback_source: None
```

## State Transitions

### Query Processing Flow

```
[RECEIVED] → [CLASSIFYING] → [ROUTING] → [EXECUTING] → [RESPONDING]
                  │                │            │
                  ▼                ▼            ▼
            QueryType      DataSource     Response
            determined     selected       generated
```

### Fallback State Machine

```
[PRIMARY_ATTEMPT]
    │
    ├─► Success → [RETURN_RESPONSE]
    │
    └─► Failure/Empty
            │
            ├─► Has fallback? → [FALLBACK_ATTEMPT]
            │                        │
            │                        ├─► Success → [RETURN_WITH_CAVEAT]
            │                        │
            │                        └─► Failure → [RETURN_NOT_FOUND]
            │
            └─► No fallback → [RETURN_NOT_FOUND]
```

## Validation Rules

### RoutingDecision Validation

| Rule | Description |
|------|-------------|
| `confidence >= 0.0 and confidence <= 1.0` | Confidence must be in valid range |
| `primary_source != None` | Must have a primary source |
| `query_type == PERSONAL_DATA → fallback_source == None` | Personal queries should not fall back to LLM |
| `indicators_matched != []` | Should have at least one matched indicator |

### Response Generation Rules

| Query Type | On Empty Result | On Error |
|------------|-----------------|----------|
| PERSONAL_DATA | "I don't have any records of [X]" | "I couldn't access your history" |
| FACTUAL_CURRENT | Fall back to LLM with caveat | "I couldn't verify that online" |
| GENERAL_KNOWLEDGE | Return LLM response | "I'm having trouble processing that" |
