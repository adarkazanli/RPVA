# Tasks: Smarter Query Routing

**Input**: Design documents from `/specs/006-smart-query-routing/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included per Constitution Principle V (TDD)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story label (US1-US5)
- Exact file paths included

---

## Phase 1: Setup

**Purpose**: Create QueryRouter module structure and base types

- [ ] T001 Create QueryType and DataSource enums in src/ara/router/query_router.py
- [ ] T002 Create RoutingDecision dataclass in src/ara/router/query_router.py
- [ ] T003 [P] Create query indicator constants (PERSONAL_INDICATORS, FACTUAL_INDICATORS) in src/ara/router/query_router.py
- [ ] T004 [P] Create empty test file tests/unit/test_query_router.py with imports

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core QueryRouter class that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create QueryRouter class skeleton with classify() method signature in src/ara/router/query_router.py
- [ ] T006 Implement is_personal_query() helper method in src/ara/router/query_router.py
- [ ] T007 Implement is_factual_query() helper method in src/ara/router/query_router.py
- [ ] T008 [P] Add "not found" response templates to src/ara/storage/queries.py
- [ ] T009 Export QueryRouter from src/ara/router/__init__.py

**Checkpoint**: QueryRouter class exists with helper methods - user story implementation can begin

---

## Phase 3: User Story 1 - Personal Data Queries Check Database First (Priority: P1) 🎯 MVP

**Goal**: Route queries with personal indicators (my, I, me, when did I) to MongoDB first; return "not found" message instead of hallucinating

**Independent Test**: Ask "When did I last exercise?" → system queries DB, returns stored data or "I don't have any exercise records"

### Tests for User Story 1

- [ ] T010 [P] [US1] Write test: personal query "When did I last exercise?" returns PERSONAL_DATA type in tests/unit/test_query_router.py
- [ ] T011 [P] [US1] Write test: personal query "What meetings did I have?" routes to DATABASE in tests/unit/test_query_router.py
- [ ] T012 [P] [US1] Write test: personal query with no DB results returns "not found" message in tests/unit/test_query_router.py
- [ ] T013 [P] [US1] Write integration test for personal query flow in tests/integration/test_routing_flow.py

### Implementation for User Story 1

- [ ] T014 [US1] Implement personal indicator pattern matching in QueryRouter.classify() in src/ara/router/query_router.py
- [ ] T015 [US1] Add PERSONAL_DATA routing logic (primary=DATABASE, fallback=None) in src/ara/router/query_router.py
- [ ] T016 [US1] Create _handle_personal_query() method in src/ara/router/orchestrator.py
- [ ] T017 [US1] Integrate QueryRouter into Orchestrator._handle_intent() for personal queries in src/ara/router/orchestrator.py
- [ ] T018 [US1] Add "not found" response generation for empty DB results in src/ara/router/orchestrator.py
- [ ] T019 [US1] Run tests and verify all US1 tests pass

**Checkpoint**: Personal queries route to DB first, return "not found" on empty results - no hallucination

---

## Phase 4: User Story 2 - Factual Queries Use Web Search (Priority: P1)

**Goal**: Route factual/time-sensitive queries (weather, distance, price) to Tavily web search first

**Independent Test**: Ask "What's the weather in Austin?" → system uses web search, returns real data

### Tests for User Story 2

- [ ] T020 [P] [US2] Write test: factual query "What's the weather?" returns FACTUAL_CURRENT type in tests/unit/test_query_router.py
- [ ] T021 [P] [US2] Write test: distance query "How far is Dallas?" routes to WEB_SEARCH in tests/unit/test_query_router.py
- [ ] T022 [P] [US2] Write test: price query "Apple stock price" routes to WEB_SEARCH in tests/unit/test_query_router.py
- [ ] T023 [P] [US2] Write integration test for factual query flow in tests/integration/test_routing_flow.py

### Implementation for User Story 2

- [ ] T024 [US2] Implement factual indicator pattern matching in QueryRouter.classify() in src/ara/router/query_router.py
- [ ] T025 [US2] Add FACTUAL_CURRENT routing logic (primary=WEB_SEARCH, fallback=LLM) in src/ara/router/query_router.py
- [ ] T026 [US2] Create _handle_factual_query() method in src/ara/router/orchestrator.py
- [ ] T027 [US2] Integrate QueryRouter into Orchestrator._handle_intent() for factual queries in src/ara/router/orchestrator.py
- [ ] T028 [US2] Run tests and verify all US2 tests pass

**Checkpoint**: Factual queries route to web search - no LLM guessing at verifiable facts

---

## Phase 5: User Story 3 - General Knowledge Uses LLM (Priority: P2)

**Goal**: Route general knowledge queries directly to LLM for fast responses

**Independent Test**: Ask "What is the capital of France?" → LLM responds quickly without web search

### Tests for User Story 3

- [ ] T029 [P] [US3] Write test: definition query "What does serendipity mean?" returns GENERAL_KNOWLEDGE type in tests/unit/test_query_router.py
- [ ] T030 [P] [US3] Write test: how-to query "How do I make eggs?" routes to LLM in tests/unit/test_query_router.py
- [ ] T031 [P] [US3] Write test: general knowledge does NOT trigger web search in tests/unit/test_query_router.py

### Implementation for User Story 3

- [ ] T032 [US3] Implement general knowledge indicator detection (definitions, how-to, math) in src/ara/router/query_router.py
- [ ] T033 [US3] Add GENERAL_KNOWLEDGE routing logic (primary=LLM, fallback=None) in src/ara/router/query_router.py
- [ ] T034 [US3] Update Orchestrator to route general knowledge directly to LLM in src/ara/router/orchestrator.py
- [ ] T035 [US3] Run tests and verify all US3 tests pass

**Checkpoint**: General knowledge queries skip external lookups for faster response

---

## Phase 6: User Story 4 - Ambiguous Query Classification (Priority: P2)

**Goal**: Handle ambiguous queries using context or ask for clarification

**Independent Test**: Ask "What about John?" with prior context → system queries DB for John-related notes

### Tests for User Story 4

- [ ] T036 [P] [US4] Write test: ambiguous query without context returns AMBIGUOUS type in tests/unit/test_query_router.py
- [ ] T037 [P] [US4] Write test: ambiguous query with context resolves to appropriate type in tests/unit/test_query_router.py
- [ ] T038 [P] [US4] Write test: clarification prompt generated for truly ambiguous queries in tests/unit/test_query_router.py

### Implementation for User Story 4

- [ ] T039 [US4] Add context parameter to QueryRouter.classify() in src/ara/router/query_router.py
- [ ] T040 [US4] Implement context-aware disambiguation logic in src/ara/router/query_router.py
- [ ] T041 [US4] Create clarification prompt generator for AMBIGUOUS queries in src/ara/router/orchestrator.py
- [ ] T042 [US4] Update Orchestrator to pass conversation context to QueryRouter in src/ara/router/orchestrator.py
- [ ] T043 [US4] Run tests and verify all US4 tests pass

**Checkpoint**: Ambiguous queries use context or ask for clarification

---

## Phase 7: User Story 5 - Graceful Fallback Chain (Priority: P3)

**Goal**: Implement fallback chain when primary source fails

**Independent Test**: Simulate web search failure → system falls back to LLM with caveat message

### Tests for User Story 5

- [ ] T044 [P] [US5] Write test: web search failure triggers LLM fallback with caveat in tests/unit/test_query_router.py
- [ ] T045 [P] [US5] Write test: database unavailable returns appropriate error message in tests/unit/test_query_router.py
- [ ] T046 [P] [US5] Write integration test for fallback chain flow in tests/integration/test_routing_flow.py

### Implementation for User Story 5

- [ ] T047 [US5] Add fallback execution logic to Orchestrator in src/ara/router/orchestrator.py
- [ ] T048 [US5] Implement caveat message generation for fallback responses in src/ara/router/orchestrator.py
- [ ] T049 [US5] Add error handling for database unavailable in src/ara/router/orchestrator.py
- [ ] T050 [US5] Add error handling for web search failure in src/ara/router/orchestrator.py
- [ ] T051 [US5] Run tests and verify all US5 tests pass

**Checkpoint**: System gracefully degrades when services fail

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation

- [ ] T052 [P] Add logging for routing decisions in src/ara/router/query_router.py
- [ ] T053 [P] Update src/ara/router/intent.py to leverage QueryRouter for intent classification
- [ ] T054 Run full test suite: pytest tests/unit/test_query_router.py tests/integration/test_routing_flow.py -v
- [ ] T055 Validate quickstart.md scenarios work end-to-end
- [ ] T056 Performance check: verify classification adds <100ms latency

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 and US2 (both P1) can proceed in parallel
  - US3 and US4 (both P2) can proceed in parallel after P1 stories
  - US5 (P3) should follow P1/P2 stories
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

| Story | Priority | Can Start After | Dependencies on Other Stories |
|-------|----------|-----------------|-------------------------------|
| US1 | P1 | Phase 2 | None |
| US2 | P1 | Phase 2 | None |
| US3 | P2 | Phase 2 | None (but US1/US2 establish patterns) |
| US4 | P2 | Phase 2 | None |
| US5 | P3 | Phase 2 | Needs routing from US1-US4 to test fallbacks |

### Parallel Opportunities

```bash
# Phase 1 - All in parallel:
T001, T002, T003, T004

# Phase 2 - Some parallel:
T005 → T006, T007 (sequential within file)
T008 (parallel - different file)

# US1 Tests - All parallel:
T010, T011, T012, T013

# US2 Tests - All parallel:
T020, T021, T022, T023

# US3 Tests - All parallel:
T029, T030, T031

# US4 Tests - All parallel:
T036, T037, T038

# US5 Tests - All parallel:
T044, T045, T046
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 (Personal queries)
4. Complete Phase 4: US2 (Factual queries)
5. **STOP and VALIDATE**: Core routing works - personal → DB, factual → web
6. Deploy/demo MVP

### Incremental Delivery

| Milestone | Stories Complete | Value Delivered |
|-----------|------------------|-----------------|
| MVP | US1 + US2 | No hallucination for personal/factual queries |
| +General | US3 | Fast LLM responses for simple queries |
| +Ambiguity | US4 | Smart handling of unclear queries |
| +Reliability | US5 | Graceful degradation on failures |

---

## Notes

- [P] tasks can run in parallel (different files)
- Tests written FIRST per TDD (Constitution Principle V)
- Each checkpoint = independently testable increment
- US1 + US2 together form the MVP (both P1 priority)
- Run tests after each implementation task
