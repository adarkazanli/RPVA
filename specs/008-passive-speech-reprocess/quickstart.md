# Quickstart: Passive Speech Interrupt and Reprocessing

**Feature**: 008-passive-speech-reprocess
**Date**: 2026-01-17

## Overview

This feature enables the voice assistant to detect when users speak during response playback, immediately stop speaking, and combine all user input for reprocessing. This creates a more natural, conversational interaction where users can add context or change their request mid-response.

## Key Concepts

### Interrupt Detection
The system continuously monitors audio input during TTS playback. When user speech energy exceeds threshold (750 RMS), playback stops within 500ms.

### Request Buffer
All user speech within a conversation turn accumulates in a buffer:
- Original request: "Research BSI"
- Interrupt 1: "in Austin"
- Combined: "Research BSI in Austin"

### Continuation Window
After the agent finishes speaking, a 5-second window allows users to add more context without re-triggering the wake word.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ InterruptMgr │←→│ AudioCapture │  │ AudioPlayback│       │
│  │              │  │              │  │              │       │
│  │ - state      │  │ - stream()   │  │ - play()     │       │
│  │ - buffer     │  │              │  │ - stop()     │       │
│  │ - window     │  │              │  │ - is_playing │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                      │                                       │
│              ┌───────┴───────┐                               │
│              │  STT/Intent   │                               │
│              │  Reprocessing │                               │
│              └───────────────┘                               │
└─────────────────────────────────────────────────────────────┘
```

## State Machine

```
IDLE ──(wake word)──→ LISTENING ──(silence)──→ PROCESSING
                                                    │
                                                    ▼
                     ┌─────────────────────── RESPONDING
                     │                              │
              (user speaks)                  (playback done)
                     │                              │
                     ▼                              ▼
               INTERRUPTED ───(2s silence)──→ PROCESSING
                     ▲                              │
                     │                              ▼
                     └─────────(user speaks)── CONTINUATION
                                                    │
                                              (5s timeout)
                                                    │
                                                    ▼
                                                  IDLE
```

## Implementation Guide

### 1. InterruptManager Setup

```python
from ara.router.interrupt import InterruptManager

# In Orchestrator.__init__
self._interrupt_manager = InterruptManager(
    capture=self._capture,
    playback=self._playback,
    on_interrupt=self._handle_interrupt,
)
```

### 2. Modified Voice Loop

```python
# In process_single_interaction()

# 1. Record and transcribe initial request
audio = self._record_speech()
text = self._transcriber.transcribe(audio)
self._interrupt_manager.set_initial_request(text)

# 2. Process and generate response
intent = self._intent_classifier.classify(text)
response = self._handle_intent(intent)
tts_audio = self._synthesizer.synthesize(response)

# 3. Play with interrupt monitoring
interrupt = self._interrupt_manager.play_with_monitoring(
    tts_audio.audio,
    tts_audio.sample_rate,
)

if interrupt:
    # 4a. Handle interrupt - wait for user to finish
    interrupt_text = self._interrupt_manager.wait_for_interrupt_complete()
    if interrupt_text:
        # Reprocess combined request
        combined = self._interrupt_manager.get_combined_request()
        # Loop back to step 2 with combined text
        ...
else:
    # 4b. No interrupt - start continuation window
    self._interrupt_manager.start_continuation_window(
        on_expire=self._end_conversation_turn,
    )
```

### 3. Playback Extension

```python
# In audio/backends/macos.py (and linux.py)

@property
def is_playing(self) -> bool:
    """Return True if audio is currently playing."""
    return self._is_playing

def stop(self) -> None:
    """Stop playback within 500ms."""
    self._stop_flag.set()
    if self._play_thread:
        self._play_thread.join(timeout=0.5)
        self._play_thread = None
    self._is_playing = False
```

## Testing Checklist

### Unit Tests (44 tests passing)
- [x] RequestBuffer accumulates segments correctly
- [x] RequestBuffer.get_combined_text() joins with spaces
- [x] ContinuationWindow expires after 5 seconds
- [x] ContinuationWindow.cancel() stops timer
- [x] InterruptState transitions follow state diagram
- [x] Special keywords (stop, wait, cancel, never mind) detected
- [x] Energy calculation works for silent/loud/empty audio

### Integration Tests
- [x] TTS stops within 500ms when user speaks
- [x] Interrupt audio is captured and transcribed
- [x] Combined request is processed correctly
- [x] Continuation window accepts input within 5 seconds
- [x] Continuation window rejects input after 5 seconds
- [x] Intent redirect with "actually" keyword works
- [x] Stop keyword pauses response

### Manual Tests
- [ ] Say "Research BSI", wait for response, say "add to action items"
- [ ] Say "Set timer", say "for 5 minutes" during response
- [ ] Say "What's the weather", let response finish, say "and tomorrow" within 5s
- [ ] Say "Stop" during response - verify agent pauses

## Configuration

```python
# Constants in ara/router/interrupt.py

INTERRUPT_THRESHOLD = 750.0      # RMS energy to trigger
SILENCE_TIMEOUT_MS = 2000        # Silence before reprocess
CONTINUATION_WINDOW_S = 5.0      # Post-response window
TTS_STOP_TIMEOUT_MS = 500        # Max stop latency
INTERRUPT_FEEDBACK_FREQ = 200    # Acknowledgment tone Hz
INTERRUPT_FEEDBACK_MS = 100      # Acknowledgment duration
```

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Interrupt not detected | Threshold too high | Lower INTERRUPT_THRESHOLD |
| False interrupts | Threshold too low | Raise INTERRUPT_THRESHOLD |
| TTS doesn't stop | Stop flag not checked | Verify chunk-based playback |
| Combined text wrong | Buffer not appending | Check RequestBuffer.append() |
| Window expires early | Timer misconfigured | Verify 5.0 second setting |

## Files Modified

| File | Change |
|------|--------|
| `src/ara/router/interrupt.py` | NEW: InterruptManager, RequestBuffer, ContinuationWindow |
| `src/ara/router/orchestrator.py` | MODIFY: Add interrupt handling to voice loop |
| `src/ara/audio/playback.py` | MODIFY: Add is_playing property to protocol |
| `src/ara/audio/backends/macos.py` | MODIFY: Implement is_playing |
| `src/ara/audio/backends/linux.py` | MODIFY: Implement is_playing |
| `src/ara/feedback/audio.py` | MODIFY: Add interrupt acknowledgment tone |
| `tests/unit/test_interrupt.py` | NEW: Unit tests for interrupt module |
| `tests/integration/test_interrupt_flow.py` | NEW: End-to-end interrupt tests |
