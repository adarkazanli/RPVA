# Research: Platform-Adaptive TTS

## Platform Detection

**Decision**: Use `platform.system()` and `platform.machine()` from Python stdlib

**Rationale**:
- No external dependencies required
- `platform.system()` returns "Darwin" for macOS, "Linux" for Raspberry Pi
- `platform.machine()` returns "arm64" or "aarch64" for ARM devices (Pi), "x86_64" for Intel Macs
- Reliable across Python versions 3.11+

**Alternatives considered**:
- `sys.platform`: Less detailed (returns "darwin" or "linux2")
- Reading `/proc/cpuinfo`: Linux-only, more complex
- `os.uname()`: Similar to platform module but less portable

**Implementation**:
```python
import platform

def detect_platform() -> str:
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin":
        return "macos"
    elif system == "Linux" and machine in ("aarch64", "armv7l"):
        return "raspberry_pi"
    else:
        return "other"
```

## macOS TTS Implementation

**Decision**: Use `subprocess` to call macOS `say` command

**Rationale**:
- `say` command is pre-installed on all macOS versions
- Provides access to all system voices including "Samantha"
- Can output to audio file (AIFF) then convert to PCM bytes
- No additional dependencies required
- Faster than Python bindings for simple synthesis

**Alternatives considered**:
- `pyttsx3`: Cross-platform but macOS voice quality inferior to native `say`
- `NSSpeechSynthesizer` via PyObjC: Requires additional dependency, more complex
- `AVSpeechSynthesizer` via Swift bridge: Too complex for this use case

**Implementation approach**:
```python
import subprocess
import tempfile

def synthesize_macos(text: str, voice: str = "Samantha") -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
        temp_path = f.name

    # Generate audio file using say command
    subprocess.run(
        ["say", "-v", voice, "-o", temp_path, text],
        check=True,
        capture_output=True,
    )

    # Read and convert to PCM (or use afconvert)
    # ... conversion logic

    return audio_bytes
```

**Voice selection**: "Samantha" - high-quality female voice, pre-installed on macOS

## Fallback Chain Design

**Decision**: Implement ordered fallback: Primary → Secondary → Mock

**Rationale**:
- Ensures system never fails silently (FR-005, SC-003)
- Graceful degradation when preferred engine unavailable
- Mock provides audible feedback even if all TTS fails

**Fallback order by platform**:

| Platform | Primary | Secondary | Fallback |
|----------|---------|-----------|----------|
| macOS | macOS native | Piper | Mock (beep) |
| Raspberry Pi | Piper | Mock (beep) | - |
| Other Linux | Piper | Mock (beep) | - |

**Implementation**:
```python
def create_synthesizer(config, use_mock=False):
    if use_mock:
        return MockSynthesizer()

    platform = detect_platform()

    if platform == "macos":
        try:
            synth = MacOSSynthesizer(voice="Samantha")
            if synth.is_available:
                return synth
        except Exception:
            pass
        # Fallback to Piper on macOS
        try:
            synth = PiperSynthesizer(...)
            if synth.is_available:
                return synth
        except Exception:
            pass

    elif platform == "raspberry_pi":
        try:
            synth = PiperSynthesizer(...)
            if synth.is_available:
                return synth
        except Exception:
            pass

    # Final fallback
    return MockSynthesizer()
```

## Audio Format Considerations

**Decision**: Convert macOS AIFF output to 16-bit PCM at 22050 Hz

**Rationale**:
- Matches existing Piper output format
- Compatible with existing audio playback pipeline
- `SynthesisResult` expects raw PCM bytes with sample_rate

**Conversion approach**:
- Use `afconvert` CLI (macOS built-in) or
- Use `wave` module to read AIFF and extract PCM

## Performance Validation

**Expected latency**:
- macOS `say` command: ~100-200ms for short phrases
- Piper TTS: ~300-400ms for short phrases (already validated)
- Both within 500ms budget

**Benchmark plan**:
- Test 10 sample phrases on each platform
- Measure p50, p95, p99 latencies
- Verify < 500ms constraint
