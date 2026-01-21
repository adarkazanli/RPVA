# Research: Claude Query Mode

**Feature**: 009-claude-query-mode
**Date**: 2026-01-21

## Research Tasks

### 1. Claude API Authentication with Claude Max Subscription

**Decision**: Use Anthropic API key stored in environment variable `ANTHROPIC_API_KEY`

**Rationale**:
- The existing codebase already uses this pattern in `src/ara/llm/cloud.py`
- `CloudLanguageModel` class already implements API key authentication via `CloudLLMConfig.from_env()`
- Claude Max subscription provides API access through the same Anthropic API
- No additional authentication flow needed beyond storing the API key

**Alternatives Considered**:
- OAuth flow: Rejected - Claude Max uses API keys, not OAuth
- Config file storage: Rejected - environment variables are more secure for credentials
- Interactive setup: Not needed - simple API key works for single-user scenario

**Implementation Notes**:
- Reuse existing `CloudLLMConfig` for consistency
- Store API key in `~/.ara/config.yaml` or environment variable
- Validate API key on first use with a simple test call

### 2. Conversation History Management

**Decision**: In-memory conversation history with explicit reset command

**Rationale**:
- Spec clarification: history persists until user says "new conversation" (FR-005)
- Claude API supports conversation context via message history in API calls
- In-memory storage is sufficient since Ara typically runs as a long-lived process
- Explicit reset gives user control without automatic timeouts

**Alternatives Considered**:
- Timeout-based session expiry: Rejected - user preferred explicit control
- Database-backed history: Overkill for single-user scenario; would add latency
- File-based persistence: Unnecessary complexity

**Implementation Notes**:
- Create `ClaudeSession` class to manage message history
- Store list of `{"role": "user"|"assistant", "content": str}` messages
- Cap history at ~20 messages to stay within context limits
- Oldest messages trimmed when approaching token limits

### 3. Internet Connectivity Check

**Decision**: HTTP HEAD request to a reliable endpoint before each Claude query

**Rationale**:
- FR-011 requires connectivity check before each query
- SC-008 requires check to complete within 2 seconds
- Simple HEAD request is lightweight and reliable

**Alternatives Considered**:
- Socket connection test: Less reliable across networks
- DNS resolution: Doesn't verify full connectivity
- Ping: May be blocked by firewalls

**Implementation Notes**:
```python
import httpx

async def check_connectivity(timeout: float = 2.0) -> bool:
    """Check internet connectivity with 2-second timeout."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.head("https://api.anthropic.com/")
            return response.status_code < 500
    except Exception:
        return False
```

### 4. Audio Waiting Indicator (Musical Loop)

**Decision**: Short looping audio file played in background thread

**Rationale**:
- Spec clarification: musical loop (short melody that repeats)
- Existing `SoundFeedback` class supports custom WAV files
- Loop should be non-intrusive but clearly audible
- Must stop immediately when response arrives (SC-007: 500ms)

**Alternatives Considered**:
- Generated tones: Less pleasant for extended waiting periods
- Speech ("Thinking..."): Could be annoying on repeat
- Silence with periodic beeps: Less clear that system is working

**Implementation Notes**:
- Add `CLAUDE_WAITING` to `FeedbackType` enum
- Create short (~2-3 second) musical loop WAV file
- Use background thread for playback with stop flag
- Existing `play_async` supports this pattern

### 5. Response Length Handling

**Decision**: Instruct Claude to provide concise responses via system prompt

**Rationale**:
- Spec clarification: summarize responses to fit 60 seconds spoken (FR-008)
- ~150 words = ~60 seconds at typical speech rate
- Better UX than truncating or chunking

**Alternatives Considered**:
- Post-processing truncation: Loses context/coherence
- Chunking with "continue?": More complex UX
- No limit: Users may get frustrated with long responses

**Implementation Notes**:
System prompt addition:
```
Provide concise responses suitable for voice output.
Limit responses to approximately 150 words (~60 seconds when spoken).
Focus on the most important information first.
```

### 6. MongoDB Schema for Claude Queries

**Decision**: Separate `claude_queries` collection with type identifiers

**Rationale**:
- FR-015 requires distinct type identifier for filtering
- FR-016 requires time-based retrieval
- Separate collection keeps Claude data organized
- Follows existing repository pattern (`InteractionRepository`)

**Alternatives Considered**:
- Same `interactions` collection with type field: Mixes different data types
- Separate database: Overkill for single feature

**Implementation Notes**:
- Collection: `claude_queries`
- Indexes: `timestamp` (descending), `session_id`, `type`
- Type field values: `"claude_query"`, `"claude_response"`

### 7. Trigger Phrase Recognition

**Decision**: Add patterns to existing `IntentClassifier` for "ask Claude" and variants

**Rationale**:
- FR-001 requires recognizing "ask Claude" and variations ("ask Claud")
- Existing pattern-based intent classification is extensible
- High confidence match needed to avoid false positives

**Alternatives Considered**:
- Separate classifier: Unnecessary complexity
- LLM-based classification: Too slow for trigger detection

**Implementation Notes**:
```python
CLAUDE_QUERY_PATTERNS = [
    r"ask\s+claude\s+(.+)",
    r"ask\s+claud\s+(.+)",  # Common mishearing
    r"hey\s+claude[,\s]+(.+)",
    r"claude[,\s]+(.+)",  # Direct address after initial activation
]
```

### 8. 30-Second Timeout and Retry

**Decision**: Async timeout with user-prompted retry option

**Rationale**:
- FR-013: 30-second timeout, then offer retry
- Spec clarification: "Claude is taking longer, try again?"
- User should have explicit control over retry

**Implementation Notes**:
```python
import asyncio

async def query_with_timeout(query: str, timeout: float = 30.0) -> str | None:
    try:
        return await asyncio.wait_for(
            self._send_to_claude(query),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return None  # Handler prompts for retry
```

## Dependencies Verified

| Dependency | Version | Purpose | Already Installed |
|------------|---------|---------|-------------------|
| anthropic | >=0.18 | Claude API client | Yes (in pyproject.toml) |
| pymongo | >=4.6 | MongoDB driver | Yes |
| httpx | - | Connectivity check | Need to verify |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Claude API rate limiting | Low | Medium | Implement exponential backoff |
| Long response times | Medium | Low | 30-second timeout + feedback |
| Context overflow | Low | Low | Cap message history at 20 |
| API key exposure | Low | High | Environment variable, never log |

## Open Questions (Resolved)

All technical questions have been resolved through research and spec clarifications. No blockers for Phase 1.
