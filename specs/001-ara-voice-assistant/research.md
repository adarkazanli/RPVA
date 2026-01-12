# Research: Ara Voice Assistant

**Date**: 2026-01-12
**Branch**: `001-ara-voice-assistant`
**Purpose**: Resolve technology choices and document decisions for implementation

## 1. Wake Word Detection

### Decision: Porcupine (primary) with OpenWakeWord fallback

### Rationale
- Porcupine provides commercial-grade accuracy with low latency (<100ms)
- Works offline with pre-trained models
- Cross-platform support (macOS, Linux, ARM64)
- OpenWakeWord as open-source alternative if licensing becomes an issue

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Porcupine | High accuracy, low latency, cross-platform | Commercial license required | **Selected** |
| OpenWakeWord | Open source, customizable | Slightly higher latency, less tested | Fallback |
| Snowboy | Popular, open source | Deprecated, no longer maintained | Rejected |
| Custom VAD + keyword | Full control | High development effort, lower accuracy | Rejected |

### Implementation Notes
- Use Porcupine Python SDK (`pvporcupine`)
- Custom wake word "Ara" requires training via Picovoice Console
- Fallback to "computer" or "jarvis" pre-built keywords for testing

---

## 2. Speech-to-Text (STT)

### Decision: faster-whisper with Whisper base.en model

### Rationale
- faster-whisper uses CTranslate2 for optimized inference (2-4x faster than original Whisper)
- base.en model balances accuracy and speed on Pi 4 (~1s for 5s audio)
- int8 quantization reduces memory usage without significant accuracy loss
- Python bindings available, works offline

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| faster-whisper | Fast, accurate, Python API | Larger than tiny model | **Selected** |
| whisper.cpp | C++ performance | Requires bindings, less convenient | Considered |
| Vosk | Very lightweight | Lower accuracy for general speech | Rejected |
| DeepSpeech | Mozilla-backed | Deprecated, accuracy issues | Rejected |
| Cloud STT | Best accuracy | Requires internet, latency, cost | Online fallback only |

### Model Selection

| Model | Size | Pi 4 Latency | Accuracy (WER) | Recommendation |
|-------|------|--------------|----------------|----------------|
| tiny.en | 75MB | ~0.5s | Good (10-15%) | Development only |
| base.en | 142MB | ~1.0s | Better (8-12%) | **Production** |
| small.en | 466MB | ~3.0s | Best (5-8%) | Too slow for Pi |

### Implementation Notes
- Use `faster-whisper` Python package
- Enable VAD filter to skip silence
- Beam size=1 for speed (beam size=5 for accuracy when needed)
- Stream audio processing when possible

---

## 3. Language Model (LLM)

### Decision: Ollama with Llama 3.2 3B Q4_K_M

### Rationale
- Ollama provides simple API and model management
- Llama 3.2 3B fits in 8GB RAM when quantized
- Q4_K_M quantization offers good quality/size tradeoff
- Local inference, no internet required
- Supports custom system prompts for voice assistant personality

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Ollama + Llama 3.2 3B | Easy setup, good quality | Requires Ollama daemon | **Selected** |
| llama.cpp direct | Lower overhead | More complex integration | Alternative |
| Phi-3 Mini | Smaller, faster | Slightly lower quality | Backup option |
| Gemma 2 2B | Google-backed | Similar to Llama, less tested | Considered |
| Claude API | Best quality | Requires internet, cost | Online enhancement only |

### Model Configuration

```yaml
model: llama-3.2-3b
quantization: Q4_K_M
context_length: 4096
max_tokens: 150  # Keep responses short for voice
temperature: 0.7
system_prompt: |
  You are Ara, a helpful voice assistant. Keep responses brief,
  conversational, and under 2 sentences. Be natural and friendly.
  Never use markdown, lists, or formatting—speak naturally.
```

### Implementation Notes
- Run Ollama as system service
- Pre-warm model on startup to reduce first-query latency
- Implement streaming for perceived responsiveness
- Track token count for context window management

---

## 4. Text-to-Speech (TTS)

### Decision: Piper TTS with en_US-lessac-medium voice

### Rationale
- Piper is optimized for Raspberry Pi (ONNX runtime)
- Medium quality voices sound natural without excessive latency
- Offline operation, no API keys needed
- Multiple voice options available

### Alternatives Considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Piper | Fast, natural, Pi-optimized | Limited voice customization | **Selected** |
| Coqui TTS | Open source, customizable | Higher latency on Pi | Rejected |
| eSpeak | Very fast, tiny | Robotic sound quality | Rejected |
| Cloud TTS | Best quality | Requires internet, cost | Online enhancement only |

### Voice Selection

| Voice | Size | Quality | Speed | Recommendation |
|-------|------|---------|-------|----------------|
| en_US-lessac-medium | 75MB | Good | Fast | **Production** |
| en_US-amy-medium | 75MB | Good | Fast | Alternative |
| en_US-lessac-high | 150MB | Better | Slower | Quality priority |

### Implementation Notes
- Pre-load voice model on startup
- Stream audio output while generating
- 22050Hz sample rate for output
- Use subprocess for TTS generation, pipe to audio playback

---

## 5. Audio I/O

### Decision: PyAudio with platform-specific backends

### Rationale
- PyAudio provides consistent API across platforms
- Uses PortAudio underneath (mature, stable)
- macOS: CoreAudio backend
- Linux: ALSA backend (PulseAudio optional)

### Platform Abstraction

```python
# Interface
class AudioCapture(Protocol):
    def start(self) -> None: ...
    def read(self, frames: int) -> bytes: ...
    def stop(self) -> None: ...

class AudioPlayback(Protocol):
    def play(self, audio: bytes, sample_rate: int) -> None: ...
    def stop(self) -> None: ...
```

### Implementation Notes
- 16kHz sample rate for STT input
- 22050Hz for TTS output
- Chunk size: 1024 frames (64ms at 16kHz)
- Use separate threads for capture and playback
- Mock implementation for CI testing

---

## 6. Logging & Storage

### Decision: SQLite + JSON Lines + Markdown

### Rationale
- SQLite: Fast queries, ACID compliant, single file
- JSON Lines: Portable, appendable, easy to process
- Markdown: Human-readable summaries

### Storage Schema

| Data | Format | Location | Retention |
|------|--------|----------|-----------|
| Interactions | SQLite | `~/.ara/ara.db` | 90 days |
| Daily logs | JSONL | `~/ara/logs/YYYY-MM-DD.jsonl` | 90 days |
| Summaries | Markdown | `~/ara/summaries/YYYY-MM-DD.md` | Indefinite |

### Implementation Notes
- WAL mode for SQLite (prevents blocking during writes)
- Atomic file writes for JSONL (write to temp, rename)
- Daily summary generation at midnight or on-demand
- Export functionality for backup/sync

---

## 7. Configuration Management

### Decision: YAML with profile inheritance

### Rationale
- YAML is human-readable and supports complex structures
- Profile inheritance reduces duplication
- Environment variable overrides for secrets

### Configuration Structure

```yaml
# base.yaml
ara:
  wake_word: "ara"
  log_level: INFO
  models:
    whisper: "base.en"
    llm: "llama-3.2-3b"
    tts: "en_US-lessac-medium"

# dev.yaml
extends: base.yaml
ara:
  log_level: DEBUG
  audio:
    mock_enabled: true

# prod.yaml
extends: base.yaml
ara:
  audio:
    input_device: "respeaker"
```

---

## 8. Testing Strategy

### Decision: pytest with fixtures and benchmarks

### Test Categories

| Category | Purpose | Tools | CI/CD |
|----------|---------|-------|-------|
| Unit | Component logic | pytest | Yes |
| Integration | Module interaction | pytest, fixtures | Yes |
| Benchmark | Latency validation | pytest-benchmark | Manual |
| Voice | STT/TTS accuracy | Pre-recorded WAV | Weekly |
| E2E | Full pipeline | Live hardware | Pre-release |

### Mock Audio System

```python
class MockAudioCapture:
    """Load audio from WAV files for testing."""

    def __init__(self, fixtures_dir: Path):
        self.fixtures_dir = fixtures_dir

    def load(self, name: str) -> AudioBuffer:
        wav_path = self.fixtures_dir / f"{name}.wav"
        return AudioBuffer.from_file(wav_path)
```

### CI Pipeline
1. Lint (ruff, mypy)
2. Unit tests
3. Integration tests (mock audio)
4. Build validation
5. Benchmark (manual trigger)

---

## 9. Cross-Platform Considerations

### Platform Differences

| Aspect | macOS | Linux (Pi) | Abstraction |
|--------|-------|------------|-------------|
| Audio backend | CoreAudio | ALSA | PyAudio |
| GPU acceleration | Metal | None (CPU) | Model config |
| Wake word binary | x86_64/ARM64 | ARM64 | Porcupine SDK |
| Python | Homebrew | apt | venv |

### Shared Code Target: 95%+

Platform-specific code limited to:
- `src/audio/platform/` (audio backends)
- `config/*.yaml` (device settings)
- `scripts/setup.sh` (installation)

---

## 10. Security Considerations

### Decision: Local-first with opt-in cloud

| Concern | Mitigation |
|---------|------------|
| Audio privacy | No raw audio storage by default |
| API keys | Environment variables, not config files |
| Network exposure | No listening ports in offline mode |
| Log security | Optional encryption at rest |

### Implementation Notes
- Never store wake word audio
- Interaction logs exclude raw audio
- Cloud API keys via `ARA_CLAUDE_API_KEY` env var
- Firewall rules documented for production deployment

---

## Summary of Decisions

| Component | Technology | Version/Model |
|-----------|------------|---------------|
| Wake Word | Porcupine | Custom "Ara" |
| STT | faster-whisper | base.en, int8 |
| LLM | Ollama | Llama 3.2 3B Q4_K_M |
| TTS | Piper | en_US-lessac-medium |
| Audio | PyAudio | Platform-specific backends |
| Storage | SQLite + JSONL | WAL mode |
| Config | PyYAML | Profile inheritance |
| Testing | pytest | With benchmarks |

**All NEEDS CLARIFICATION items resolved. Ready for Phase 1.**
