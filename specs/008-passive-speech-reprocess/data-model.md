# Data Model: Passive Speech Interrupt and Reprocessing

**Feature**: 008-passive-speech-reprocess
**Date**: 2026-01-17

## Entities

### InterruptState (Enum)

Represents the current state of the interrupt handling system.

| Value | Description |
|-------|-------------|
| `IDLE` | No active conversation turn, waiting for wake word |
| `LISTENING` | Recording initial user request |
| `PROCESSING` | Running STT/intent/LLM on user input |
| `RESPONDING` | TTS playback in progress, monitoring for interrupts |
| `INTERRUPTED` | User spoke during response, accumulating input |
| `CONTINUATION` | 5-second window after response, listening for additions |

**State Transitions**:
```
IDLE → (wake word) → LISTENING
LISTENING → (silence timeout) → PROCESSING
PROCESSING → (response ready) → RESPONDING
RESPONDING → (user speaks) → INTERRUPTED
RESPONDING → (playback complete) → CONTINUATION
INTERRUPTED → (2s silence) → PROCESSING (reprocess)
CONTINUATION → (user speaks) → INTERRUPTED
CONTINUATION → (5s timeout) → IDLE
```

### RequestBuffer

Accumulates user speech segments within a single conversation turn.

| Field | Type | Description |
|-------|------|-------------|
| `segments` | `list[BufferSegment]` | Ordered list of user input segments |
| `created_at` | `datetime` | When first segment was added |
| `last_updated` | `datetime` | When most recent segment was added |

**Validation Rules**:
- `segments` must have at least one entry after LISTENING phase
- `last_updated >= created_at`

**Operations**:
- `append(text: str)`: Add new segment with current timestamp
- `get_combined_text() -> str`: Return all segments joined by space
- `clear()`: Reset buffer for new conversation turn

### BufferSegment

Single speech segment within the request buffer.

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Transcribed user speech |
| `timestamp` | `datetime` | When this segment was captured |
| `is_interrupt` | `bool` | True if captured during RESPONDING/CONTINUATION state |

**Validation Rules**:
- `text` must be non-empty after stripping whitespace
- `timestamp` must be valid datetime

### InterruptEvent

Represents a detected user speech interrupt.

| Field | Type | Description |
|-------|------|-------------|
| `audio_data` | `bytes` | Raw audio captured during interrupt |
| `energy_level` | `float` | RMS energy that triggered detection |
| `detected_at` | `datetime` | When interrupt was first detected |
| `duration_ms` | `int` | Duration of interrupt audio |

**Validation Rules**:
- `energy_level >= INTERRUPT_THRESHOLD` (750)
- `duration_ms > 0`

### ContinuationWindow

Manages the post-response continuation period.

| Field | Type | Description |
|-------|------|-------------|
| `started_at` | `datetime` | When TTS playback completed |
| `expires_at` | `datetime` | When window closes (started_at + 5 seconds) |
| `timer` | `Timer | None` | Background timer for expiration |
| `is_active` | `bool` | True if window is currently open |

**Validation Rules**:
- `expires_at = started_at + timedelta(seconds=5)`
- `is_active = current_time < expires_at`

**Operations**:
- `start()`: Begin 5-second countdown
- `cancel()`: Close window early (user spoke or new request)
- `reset()`: Restart 5-second countdown (after interrupt processed)

## Relationships

```
InterruptManager
├── state: InterruptState
├── request_buffer: RequestBuffer
│   └── segments: list[BufferSegment]
├── continuation_window: ContinuationWindow
└── current_interrupt: InterruptEvent | None
```

## Constants

| Name | Value | Description |
|------|-------|-------------|
| `INTERRUPT_THRESHOLD` | 750.0 | Minimum RMS energy to trigger interrupt |
| `SILENCE_TIMEOUT_MS` | 2000 | Milliseconds of silence before reprocessing |
| `CONTINUATION_WINDOW_S` | 5.0 | Seconds after response to accept continuations |
| `TTS_STOP_TIMEOUT_MS` | 500 | Maximum time to stop TTS playback |
| `INTERRUPT_FEEDBACK_FREQ` | 200 | Hz frequency for interrupt acknowledgment tone |
| `INTERRUPT_FEEDBACK_MS` | 100 | Duration of interrupt acknowledgment tone |

## Data Flow

```
1. User speaks → BufferSegment(text, timestamp, is_interrupt=False)
2. Agent responds → InterruptState.RESPONDING
3. User interrupts → InterruptEvent captured
4. TTS stops → InterruptEvent.audio_data → STT
5. STT result → BufferSegment(text, timestamp, is_interrupt=True)
6. Silence detected → RequestBuffer.get_combined_text()
7. Reprocess → Intent classification on combined text
8. New response → InterruptState.RESPONDING (loop back to 3)
9. No interrupt → InterruptState.CONTINUATION
10. 5s timeout → InterruptState.IDLE, RequestBuffer.clear()
```

## Memory Considerations

- **RequestBuffer**: Stores only text, not audio. Typical turn: <500 chars
- **InterruptEvent**: Temporary, audio discarded after STT
- **ContinuationWindow**: Single timer object, minimal footprint
- **Total estimated**: <10KB per active conversation turn
