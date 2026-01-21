# Data Model: Platform-Adaptive TTS

## Entities

### Platform (Enum)

Represents the detected operating system and architecture.

| Value | Description |
|-------|-------------|
| `MACOS` | macOS (Darwin) - any architecture |
| `RASPBERRY_PI` | Linux on ARM (aarch64, armv7l) |
| `OTHER` | Any other platform (generic Linux, Windows) |

### SynthesisResult (Existing - No Changes)

Result of text-to-speech synthesis.

| Field | Type | Description |
|-------|------|-------------|
| `audio` | `bytes` | Raw PCM audio data |
| `sample_rate` | `int` | Audio sample rate in Hz (typically 22050) |
| `duration_ms` | `int` | Audio duration in milliseconds |
| `latency_ms` | `int` | Synthesis latency in milliseconds |

### Synthesizer (Protocol - No Changes)

Interface that all TTS implementations must satisfy.

| Method | Returns | Description |
|--------|---------|-------------|
| `synthesize(text)` | `SynthesisResult` | Convert text to speech audio |
| `set_voice(voice_id)` | `None` | Set voice for synthesis |
| `set_speed(speed)` | `None` | Set speech speed multiplier |
| `get_available_voices()` | `list[str]` | List available voice IDs |

## New Implementations

### MacOSSynthesizer

macOS-specific TTS implementation using the native `say` command.

| Property | Type | Description |
|----------|------|-------------|
| `_voice` | `str` | Voice name (default: "Samantha") |
| `_speed` | `float` | Speed multiplier (default: 1.0) |
| `is_available` | `bool` | True if `say` command exists |

**Implements**: `Synthesizer` protocol

### PiperSynthesizer (Existing - No Changes)

Piper TTS implementation for Raspberry Pi.

### MockSynthesizer (Existing - No Changes)

Mock implementation for testing and fallback.

## Relationships

```
Platform (enum)
    │
    ▼
create_synthesizer()  ───detects───▶ Platform
    │
    │ creates appropriate
    ▼
┌─────────────────────┐
│    Synthesizer      │◀──protocol
│     (Protocol)      │
└─────────────────────┘
         ▲
         │ implements
         │
    ┌────┴────┬─────────────┐
    │         │             │
┌───┴───┐ ┌───┴───┐  ┌──────┴──────┐
│ macOS │ │ Piper │  │    Mock     │
│Synth  │ │Synth  │  │   Synth     │
└───────┘ └───────┘  └─────────────┘
```

## State Transitions

No state machines - synthesizers are stateless beyond configuration (voice, speed).

## Validation Rules

1. **Platform detection**: Must return a valid `Platform` enum value (never None)
2. **Voice parameter**: Must be a non-empty string
3. **Speed parameter**: Must be between 0.5 and 2.0
4. **Audio output**: Must be valid 16-bit PCM bytes with correct sample_rate
