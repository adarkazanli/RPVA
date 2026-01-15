# Feature Specification: Smarter Query Routing

**Feature Branch**: `006-smart-query-routing`
**Created**: 2026-01-14
**Status**: Draft
**Input**: User description: "Smarter Query Routing - Improve reliability of deciding when to use LLM vs local MongoDB vs web search (Tavily). Features: 1) Detect personal queries (my/I/when did I) and always check DB first, 2) Detect factual/time-sensitive queries and force web search, 3) Prevent LLM from hallucinating personal data or facts, 4) Use LLM to help classify ambiguous queries. Goal: Reliable routing so users get accurate answers from the right source."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Personal Data Queries Check Database First (Priority: P1)

As a user, I want questions about my personal data (activities, notes, history) to be answered from my stored data rather than the LLM making up answers, so that I get accurate information about myself.

**Why this priority**: This directly addresses the core problem of LLM hallucinating personal data. Users lose trust when the assistant fabricates information about their own activities.

**Independent Test**: Can be tested by asking "When did I last exercise?" and verifying the system queries the database rather than generating a made-up answer.

**Acceptance Scenarios**:

1. **Given** user has logged "workout" activity yesterday, **When** user asks "When did I last exercise?", **Then** system queries database and responds with accurate date/time from stored data
2. **Given** user has no exercise data in database, **When** user asks "When did I last exercise?", **Then** system responds "I don't have any exercise records" (not a fabricated answer)
3. **Given** user asks "What meetings did I have this week?", **When** the system processes this, **Then** it routes to database query and returns actual stored meeting data
4. **Given** user asks "Did I mention buying groceries?", **When** the system processes this, **Then** it searches stored notes/interactions rather than guessing

---

### User Story 2 - Factual Queries Use Web Search (Priority: P1)

As a user, I want factual questions (weather, distances, current events, prices) to be answered via web search rather than the LLM guessing, so that I get accurate, up-to-date information.

**Why this priority**: LLM hallucination of facts (wrong distances, made-up weather) destroys user trust. Factual queries must use authoritative sources.

**Independent Test**: Can be tested by asking "What's the weather in Austin?" and verifying the system uses web search rather than generating a guess.

**Acceptance Scenarios**:

1. **Given** user asks "What's the weather in Austin?", **When** the system processes this, **Then** it routes to web search and returns real weather data
2. **Given** user asks "How far is Austin from Dallas?", **When** the system processes this, **Then** it routes to web search and returns accurate distance
3. **Given** user asks "What's the stock price of Apple?", **When** the system processes this, **Then** it routes to web search for current price (not an outdated LLM guess)
4. **Given** user asks "What's in the news today?", **When** the system processes this, **Then** it routes to web search for current headlines

---

### User Story 3 - General Knowledge Uses LLM (Priority: P2)

As a user, I want general knowledge questions that don't require current data or personal history to be answered quickly by the LLM, so that I get fast responses for simple queries.

**Why this priority**: Not everything needs web search or database lookup. Simple questions like "What's the capital of France?" should be fast.

**Independent Test**: Can be tested by asking "What is the capital of France?" and verifying quick LLM response without unnecessary web search.

**Acceptance Scenarios**:

1. **Given** user asks "What is the capital of France?", **When** the system processes this, **Then** it uses LLM directly and responds quickly
2. **Given** user asks "How do I make scrambled eggs?", **When** the system processes this, **Then** it uses LLM for recipe guidance
3. **Given** user asks "What does 'serendipity' mean?", **When** the system processes this, **Then** it uses LLM for definition
4. **Given** user asks a math question "What's 15% of 200?", **When** the system processes this, **Then** it uses LLM to calculate

---

### User Story 4 - Ambiguous Query Classification (Priority: P2)

As a user, I want ambiguous queries to be intelligently classified so that the system picks the right data source even when my question could be interpreted multiple ways.

**Why this priority**: Many natural language queries are ambiguous. Smart classification prevents misrouting.

**Independent Test**: Can be tested with ambiguous queries like "What about John?" and verifying the system uses context or asks for clarification.

**Acceptance Scenarios**:

1. **Given** user previously discussed "John" in a meeting note, **When** user asks "What about John?", **Then** system uses conversation context to query database for John-related notes
2. **Given** no context exists, **When** user asks an ambiguous question like "What time?", **Then** system asks for clarification rather than guessing
3. **Given** user asks "Tell me about Tesla", **When** the system processes this, **Then** it determines if user means the company (web search) or a personal note about Tesla (database)

---

### User Story 5 - Graceful Fallback Chain (Priority: P3)

As a user, I want the system to try multiple sources in a logical order when the primary source fails, so that I still get useful answers.

**Why this priority**: Reliability feature - if web search fails, the system should gracefully fall back rather than giving up.

**Independent Test**: Can be tested by simulating web search failure and verifying fallback to LLM with appropriate caveats.

**Acceptance Scenarios**:

1. **Given** user asks a factual question and web search fails, **When** the system processes this, **Then** it falls back to LLM with caveat "I couldn't verify this online, but..."
2. **Given** user asks a personal question and database is unavailable, **When** the system processes this, **Then** it informs user that history is temporarily unavailable
3. **Given** user asks a question and LLM is unavailable, **When** the system processes this, **Then** it attempts web search as fallback

---

### Edge Cases

- What happens when a query matches multiple categories (e.g., "What's my usual workout time compared to average?")?
  - System breaks down into components: personal data (my workout time) + general knowledge (average), queries both sources
- What happens when web search returns no results?
  - System falls back to LLM with caveat about unverified information
- What happens when database query returns no results for a personal question?
  - System clearly states "I don't have that information stored" rather than making up an answer
- What happens when the query contains both personal and factual elements?
  - System identifies and queries each component separately, then combines results
- What happens when user explicitly requests a specific source ("Search the web for X")?
  - System honors explicit request and uses specified source

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect personal queries containing indicators (my, I, me, when did I, what did I, did I mention) and route to database first
- **FR-002**: System MUST detect factual/time-sensitive queries (weather, distance, price, news, current, today) and route to web search
- **FR-003**: System MUST route general knowledge queries to LLM without unnecessary external lookups
- **FR-004**: System MUST NOT generate fabricated personal data when no matching records exist in database
- **FR-005**: System MUST NOT generate fabricated factual data (distances, weather, prices) without verification
- **FR-006**: System MUST clearly indicate when information could not be verified ("I don't have that information" vs making it up)
- **FR-007**: System MUST implement fallback chain: primary source -> secondary source -> inform user of limitation
- **FR-008**: System MUST honor explicit source requests from user ("search the web for...", "check my history for...")
- **FR-009**: System MUST use conversation context to help classify ambiguous queries
- **FR-010**: System MUST ask for clarification when query is ambiguous and no context is available

### Key Entities

- **QueryType**: Classification of incoming query (personal_data, factual_current, general_knowledge, ambiguous)
- **DataSource**: Available sources for answering (database, web_search, llm)
- **RoutingDecision**: The selected source(s) for a query with confidence score and fallback chain
- **QueryIndicators**: Patterns and keywords that suggest query type (personal pronouns, time-sensitivity markers, factual keywords)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Personal data queries are correctly routed to database 95% of the time
- **SC-002**: Factual/time-sensitive queries are correctly routed to web search 90% of the time
- **SC-003**: Zero fabricated personal data responses (when data doesn't exist, system says so)
- **SC-004**: Zero fabricated factual responses for verifiable facts (distances, weather, prices)
- **SC-005**: Query classification adds less than 100ms latency to response time
- **SC-006**: Fallback chain successfully provides alternative response 80% of the time when primary source fails
- **SC-007**: Users report higher trust in responses compared to baseline (qualitative feedback)

## Assumptions

- Query classification can be done locally without external API calls
- Personal data indicators (my, I, me) are reliable signals for database queries
- Time-sensitivity indicators (weather, today, current, price) are reliable signals for web search
- LLM responses for general knowledge are acceptable without real-time verification
- Conversation context from current session is available for disambiguation
- Web search (Tavily) and database (MongoDB) are the only external data sources
