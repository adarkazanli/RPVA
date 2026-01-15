# Research: Smarter Query Routing

**Feature**: 006-smart-query-routing
**Date**: 2026-01-14

## Research Tasks

### 1. Current Routing Flow Analysis

**Question**: How does the current system route queries?

**Findings**:
- `IntentClassifier` (src/ara/router/intent.py) uses regex patterns to classify intents
- `Orchestrator._handle_intent()` routes to specific handlers based on `IntentType`
- Unmatched queries fall through to LLM via `GENERAL_QUESTION` intent
- Web search triggers only on explicit patterns (e.g., "search for X", "weather in X")

**Current Intent Types**:
- `TIME_QUERY`, `DATE_QUERY` → Local handlers (no DB/web)
- `TIMER_SET/CANCEL/QUERY` → Timer manager
- `REMINDER_SET/CANCEL/QUERY` → Reminder manager
- `HISTORY_QUERY` → MongoDB interactions collection
- `DURATION_QUERY`, `ACTIVITY_SEARCH` → MongoDB activities collection
- `EVENT_LOG` → MongoDB events collection
- `WEB_SEARCH` → Tavily search
- `GENERAL_QUESTION` → LLM (default fallback)

**Gap Identified**: No pre-routing analysis to determine if a query should check DB first or force web search. The LLM gets queries that should have been routed elsewhere.

### 2. Personal Query Indicators

**Question**: What patterns indicate a query is about personal data?

**Decision**: Use keyword-based detection with personal pronouns and possessives.

**Rationale**: Simple, fast, and accurate for common patterns. No need for ML-based classification.

**Indicators** (high confidence):
- First-person pronouns: "I", "me", "my", "mine"
- Possessive patterns: "my X", "when did I", "what did I", "did I mention"
- History references: "last time", "yesterday", "this week", "recently"
- Activity references: "how long was I", "when did I start", "what was I doing"

**Examples**:
- "When did I last exercise?" → PERSONAL (check DB)
- "What meetings did I have?" → PERSONAL (check DB)
- "Did I mention buying groceries?" → PERSONAL (check DB)
- "What's my usual workout time?" → PERSONAL (check DB)

### 3. Factual/Time-Sensitive Query Indicators

**Question**: What patterns indicate a query needs current/factual data from the web?

**Decision**: Use keyword-based detection for time-sensitive and verifiable facts.

**Rationale**: Certain topics (weather, prices, news, distances) change frequently or are easily verifiable - LLM should not guess these.

**Indicators** (high confidence):
- Weather: "weather", "temperature", "forecast", "rain", "sunny"
- Prices: "price", "cost", "stock", "worth"
- News: "news", "headlines", "latest", "current events"
- Distance/Directions: "how far", "distance", "directions to", "drive to"
- Time-sensitive: "right now", "today", "current", "latest"
- Sports: "score", "who won", "game"

**Examples**:
- "What's the weather in Austin?" → FACTUAL (web search)
- "How far is Dallas from here?" → FACTUAL (web search)
- "What's Apple stock price?" → FACTUAL (web search)
- "What's in the news?" → FACTUAL (web search)

### 4. General Knowledge Indicators

**Question**: What queries can the LLM answer reliably without external data?

**Decision**: Route to LLM when query is not personal and not time-sensitive factual.

**Rationale**: LLMs have good general knowledge for static facts, definitions, explanations, and how-to content.

**Indicators**:
- Definitions: "what is", "what does X mean", "define"
- Static facts: "capital of", "invented", "who wrote"
- How-to: "how do I", "how to", "explain"
- Math: "calculate", "what's X plus Y", "percent of"

**Examples**:
- "What's the capital of France?" → GENERAL (LLM)
- "How do I make scrambled eggs?" → GENERAL (LLM)
- "What does serendipity mean?" → GENERAL (LLM)
- "What's 15% of 200?" → GENERAL (LLM)

### 5. Fallback Chain Design

**Question**: What should happen when the primary source fails or returns no results?

**Decision**: Implement ordered fallback with appropriate messaging.

| Primary Source | On Failure/Empty | Message Pattern |
|----------------|------------------|-----------------|
| Database | Say "I don't have that" | "I don't have any records of [X]" |
| Web Search | Try LLM with caveat | "I couldn't verify online, but..." |
| LLM | Report error | "I'm having trouble processing that" |

**Rationale**: Users prefer an honest "I don't know" over fabricated information. Fallback to LLM for factual queries should include uncertainty caveat.

### 6. Query Classification Flow

**Decision**: Three-stage classification before intent handling.

```
Query → Stage 1: Personal Check
         ├─ Has personal indicators? → Check DB first
         │   └─ DB has data? → Return DB answer
         │   └─ DB empty? → Return "I don't have that"
         └─ No personal indicators → Stage 2

      → Stage 2: Factual Check
         ├─ Has factual indicators? → Web search first
         │   └─ Web success? → Return web answer
         │   └─ Web fail? → LLM with caveat
         └─ No factual indicators → Stage 3

      → Stage 3: General Knowledge
         └─ Route to LLM directly
```

**Rationale**: Priority order (personal → factual → general) prevents hallucination of personal data (most harmful) and factual data (embarrassing).

## Alternatives Considered

### ML-Based Intent Classification
- **Rejected**: Adds latency and complexity for marginal accuracy gains
- **Why simple is better**: Keyword patterns catch 95%+ of cases, no training data needed

### LLM-Assisted Routing
- **Rejected**: Adding LLM call for routing adds 2-4 seconds latency
- **Why simple is better**: Pattern matching is <10ms, LLM classification would be 2000ms+

### Always Check All Sources
- **Rejected**: Would add significant latency to every query
- **Why simple is better**: Route to one source based on query type, use fallback only on failure

## Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Classification method | Keyword patterns | Fast (<10ms), accurate, no ML overhead |
| Personal query routing | DB first, then "not found" | Prevents hallucination of personal data |
| Factual query routing | Web first, then LLM with caveat | Prevents wrong facts |
| General query routing | LLM direct | Fast for static knowledge |
| Fallback strategy | Ordered chain with messaging | Graceful degradation, honest responses |
