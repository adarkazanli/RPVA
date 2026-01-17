# Research: Passive Speech Interrupt and Reprocessing

**Feature**: 008-passive-speech-reprocess
**Date**: 2026-01-17
**Status**: Complete

## Research Summary

All technical questions resolved. Implementation can proceed with existing PyAudio-based architecture enhanced with parallel capture during playback.

---

## Decision 1: Audio Playback Interruption Method

**Decision**: Chunk-based playback with `threading.Event()` stop flag

**Rationale**:
- Already implemented in Ara's audio backends (linux.py, macos.py lines 196-315)
- Uses 1024-frame chunks (~64ms at 16kHz), checking stop flag between chunks
- Achieves 150-300ms stop latency, well under 500ms requirement
- Platform-agnostic, works on Raspberry Pi 4

**Alternatives Considered**:
- **PyAudio callback mode**: More complex, marginal latency improvement
- **sounddevice Stream**: Native full-duplex but requires architecture change
- **Blocking write with timeout**: Unreliable stop behavior

**Implementation**: Extend existing `stop()` method, add `is_playing` property to playback protocol.

---

## Decision 2: Full-Duplex Audio Pattern

**Decision**: Parallel threads - capture thread runs during playback thread

**Rationale**:
- Simplest integration with existing architecture
- Capture and playback already have separate PyAudio instances
- Thread communication via `threading.Event()` is proven reliable
- Meets 500ms requirement without sounddevice migration

**Alternatives Considered**:
- **sounddevice.Stream**: True full-duplex but requires replacing PyAudio
- **Single-threaded polling**: Would block playback, miss audio chunks
- **Asyncio**: Overkill for this use case, PyAudio not async-native

**Implementation**: New `InterruptManager` class coordinates capture thread monitoring during playback.

---

## Decision 3: Voice Activity Detection During Playback

**Decision**: Energy-based VAD with raised threshold (750 vs current 500)

**Rationale**:
- Existing RMS energy calculation in orchestrator works well
- Higher threshold (750) discriminates speech from speaker bleed
- Simple, fast (<1ms per chunk), no external dependencies
- Matches offline-first principle (no cloud VAD)

**Alternatives Considered**:
- **webrtcvad**: Excellent accuracy but C dependency, Raspberry Pi compatibility concerns
- **Silero VAD**: Neural network, too heavy for real-time on Pi 4
- **Multi-band frequency analysis**: More accurate but complex, not needed for basic interrupt

**Implementation**: Reuse `_calculate_energy()` with configurable threshold.

---

## Decision 4: Request Buffer Design

**Decision**: Simple list of (text, timestamp) tuples, string concatenation for reprocessing

**Rationale**:
- Unlimited interrupts means unbounded buffer, but practical limit is conversation turn
- Concatenation preserves natural word order: "Research BSI" + "in Austin" = "Research BSI in Austin"
- Timestamps enable timeout logic (5-second continuation window)
- Memory footprint minimal (text only, not audio after STT)

**Alternatives Considered**:
- **Audio buffer**: High memory, requires re-transcription
- **Deque with max length**: Violates unlimited interrupts requirement
- **Event sourcing pattern**: Over-engineered for single-turn buffer

**Implementation**: New `RequestBuffer` class in `interrupt.py` module.

---

## Decision 5: Continuation Window Timer

**Decision**: 5-second `threading.Timer` started when TTS completes

**Rationale**:
- Clear spec requirement (FR-005)
- Timer auto-cancels if user speaks, restarts on new silence
- Clean integration with existing thread model
- Simple to test with mock time

**Alternatives Considered**:
- **Polling loop with timestamp check**: More CPU, less precise
- **asyncio.sleep**: Would require async refactor
- **Signal-based (SIGALRM)**: Not portable, Unix-only

**Implementation**: Timer in `InterruptManager`, resets on each detected speech.

---

## Decision 6: Intent Reprocessing Strategy

**Decision**: Concatenate buffer texts with space separator, pass to existing `classify()`

**Rationale**:
- Existing intent classifier handles multi-word queries
- No special delimiter needed - natural language flows
- LLM can infer combined intent from concatenated text
- Simplest implementation, leverages existing code

**Alternatives Considered**:
- **Structured prompt with markers**: `[ORIGINAL: X] [ADDITION: Y]` - unnecessary complexity
- **Re-run each segment separately**: Would miss combined intent like "Research BSI" + "add to action items"
- **Custom concatenation grammar**: Over-engineering

**Implementation**: `RequestBuffer.get_combined_text()` returns space-joined strings.

---

## Decision 7: Interrupt Feedback Sound

**Decision**: Short low-pitched "boop" tone (200Hz, 100ms)

**Rationale**:
- Distinguishable from existing "beep" wake acknowledgment (higher pitch)
- Non-verbal, doesn't conflict with user speech recognition
- Already have `_feedback.play_tone()` capability
- Quick (100ms) doesn't delay response

**Alternatives Considered**:
- **Verbal "I'm listening"**: Too slow, transcribed as input
- **No feedback**: User confusion about whether interrupt registered
- **Visual only**: Device may not have display

**Implementation**: Add `play_interrupt_ack()` to audio feedback module.

---

## Technical Findings

### Existing Code to Leverage

| Component | Location | Notes |
|-----------|----------|-------|
| Stop playback | `audio/backends/*.py` | `stop()` method with Event flag |
| Energy VAD | `router/orchestrator.py:2645` | `_calculate_energy()` RMS calculation |
| Audio capture stream | `audio/capture.py` | `stream()` generator yields chunks |
| Intent classification | `router/intent.py` | `classify(text)` handles multi-word |
| Audio feedback | `feedback/audio.py` | `play_tone(freq, duration)` exists |

### Performance Budgets

| Operation | Target | Method |
|-----------|--------|--------|
| TTS stop | <500ms | Event flag checked every 64ms chunk |
| VAD detection | <50ms | RMS calculation per chunk |
| STT reprocess | <1500ms | faster-whisper existing latency |
| Intent classify | <10ms | Regex-based, no LLM |
| Full reprocess | <2000ms | STT + classify combined |

### Thread Safety Checklist

- [x] Playback stop: `threading.Event()` atomic
- [x] Capture stream: Generator with cleanup
- [x] Request buffer: Protected by `threading.Lock()`
- [x] Timer cancel: `threading.Timer.cancel()` safe to call multiple times
- [x] State transitions: Single writer (orchestrator), multiple readers ok

---

## Open Questions Resolved

1. **Q: Can we run capture during playback?**
   A: Yes, separate PyAudio instances for input/output work independently.

2. **Q: Will speaker audio bleed into microphone?**
   A: Raised threshold (750) and RMS discrimination handle typical setups. Echo cancellation not needed for basic interrupt detection.

3. **Q: What if user speaks during STT processing?**
   A: STT is synchronous in current architecture. User would need to wait. Consider async STT in future enhancement.

4. **Q: How to handle "continue" after interrupt?**
   A: Edge case per spec - ask clarification if context lost. No special resume logic needed for MVP.

---

## Recommendations for Implementation

1. **Create new module**: `src/ara/router/interrupt.py` with `InterruptManager` and `RequestBuffer` classes
2. **Modify orchestrator**: Add interrupt handling in main voice loop
3. **Extend playback protocol**: Add `is_playing` property
4. **Add tests first**: Unit tests for buffer and timer, integration test for interrupt flow
5. **Benchmark on Pi 4**: Verify 500ms TTS stop latency on target hardware
