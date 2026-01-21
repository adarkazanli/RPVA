# Quickstart: Platform-Adaptive TTS

## Overview

This feature adds automatic platform detection to select the best TTS engine:
- **macOS**: Uses native `say` command with "Samantha" voice
- **Raspberry Pi**: Uses Piper TTS with pre-installed models
- **Other**: Falls back to Piper or Mock synthesizer

## Usage

No changes to existing code! The `create_synthesizer()` function automatically detects the platform:

```python
from ara.tts import create_synthesizer

# Automatically selects best TTS for current platform
synth = create_synthesizer()

# Synthesize speech
result = synth.synthesize("Hello, world!")

# Play audio (result.audio contains PCM bytes)
play_audio(result.audio, result.sample_rate)
```

## Integration Scenarios

### Scenario 1: Development on macOS

```python
# On macOS, automatically uses native TTS
synth = create_synthesizer()
# → MacOSSynthesizer with "Samantha" voice

result = synth.synthesize("Testing voice output")
# Uses /usr/bin/say command internally
```

### Scenario 2: Production on Raspberry Pi

```python
# On Raspberry Pi, automatically uses Piper
synth = create_synthesizer()
# → PiperSynthesizer with en_US-lessac-medium voice

result = synth.synthesize("Testing voice output")
# Uses Piper ONNX model
```

### Scenario 3: Testing with Mock

```python
# Force mock synthesizer for unit tests
synth = create_synthesizer(use_mock=True)
# → MockSynthesizer (generates simple tone)

result = synth.synthesize("Test phrase")
# Returns synthetic audio without TTS engine
```

### Scenario 4: Fallback on Missing Engine

```python
# If macOS TTS fails, falls back to Piper
# If Piper fails, falls back to Mock
synth = create_synthesizer()

# System logs which engine was selected:
# "TTS: Using MacOSSynthesizer" or
# "TTS: MacOS not available, falling back to Piper" or
# "TTS: Using MockSynthesizer (fallback)"
```

## Platform Detection

```python
from ara.tts.platform import detect_platform, Platform

platform = detect_platform()

if platform == Platform.MACOS:
    print("Running on macOS")
elif platform == Platform.RASPBERRY_PI:
    print("Running on Raspberry Pi")
else:
    print("Running on other platform")
```

## Voice Configuration

The voice is pre-configured per platform:

| Platform | Voice | Notes |
|----------|-------|-------|
| macOS | Samantha | High-quality system voice |
| Raspberry Pi | en_US-lessac-medium | Piper neural voice |

No user configuration is needed or supported (per spec requirements).

## Troubleshooting

### macOS: "say command not found"

The `say` command should be pre-installed. If missing:
```bash
# Check if say exists
which say
# Should output: /usr/bin/say
```

### Raspberry Pi: "Piper models not found"

Run the setup script to download models:
```bash
./scripts/download_models.sh
```

### All Platforms: "Using MockSynthesizer (fallback)"

This means both primary and secondary TTS engines failed. Check:
1. macOS: Is the `say` command working?
2. Raspberry Pi: Are Piper models installed?
3. Check logs for specific error messages

## Performance

Expected synthesis latency for "Hello, how are you today?":

| Platform | Latency | Within Budget? |
|----------|---------|----------------|
| macOS | ~150ms | ✅ (< 500ms) |
| Raspberry Pi | ~350ms | ✅ (< 500ms) |
| Mock | ~10ms | ✅ (< 500ms) |
