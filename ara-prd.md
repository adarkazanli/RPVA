# Ara Voice Assistant — Product Requirements Document

**Version:** 1.0  
**Date:** January 12, 2026  
**Author:** Ammar Darkazanli  
**Status:** Draft

---

## Executive Summary

Ara is a privacy-first, offline-capable voice assistant designed to run on edge hardware (Raspberry Pi 4). The system prioritizes low latency, high accuracy, and complete functionality without internet connectivity, while supporting on-demand cloud features when available. All interactions are logged and compiled into structured daily summaries for extended use beyond individual sessions.

---

## Product Vision

**"A voice assistant that respects your privacy, works anywhere, and remembers everything."**

Ara differentiates from cloud-dependent assistants (Alexa, Google Assistant, Siri) by:
- Operating fully offline with no data leaving the device
- Providing consistent performance regardless of network availability
- Maintaining comprehensive conversation history under user control
- Supporting seamless internet connectivity for enhanced capabilities when desired

---

## Target Environments

| Environment | Primary Use Cases | Hardware Config |
|-------------|-------------------|-----------------|
| **Kitchen** | Timers, recipes, unit conversions, hands-free queries | Pi 4 + USB mic + speaker |
| **Car** | Navigation queries, reminders, hands-free messaging | Pi 4 + car audio integration |
| **Office** | Quick calculations, note-taking, schedule queries | Pi 4 + desk mic setup |

---

## Core Requirements

### 1. Offline-First Operation

**Requirement:** Ara must function completely without internet connectivity.

| Component | Offline Solution | Fallback |
|-----------|------------------|----------|
| Wake Word Detection | Local model (Porcupine/OpenWake) | Always local |
| Speech-to-Text (STT) | Whisper.cpp (local) | Cloud STT when online |
| Language Model (LLM) | Llama 3.2 3B / Phi-3 Mini (local) | Claude API when online |
| Text-to-Speech (TTS) | Piper TTS (local) | Cloud TTS when online |

**Acceptance Criteria:**
- [ ] System boots and responds to wake word with no network
- [ ] Full conversation flow works airplane mode
- [ ] No errors or degraded UX when offline
- [ ] Clear indication of online/offline status

---

### 2. Latency Requirements

**Target:** Sub-2-second end-to-end response time for typical queries.

| Stage | Target Latency | Maximum Acceptable |
|-------|----------------|-------------------|
| Wake word detection | < 100ms | 200ms |
| Speech-to-Text | < 500ms | 1000ms |
| LLM inference | < 800ms | 1500ms |
| Text-to-Speech | < 300ms | 500ms |
| **Total E2E** | **< 1.7s** | **< 3.2s** |

**Optimization Strategies:**
- Streaming STT (process as audio arrives)
- Streaming TTS (begin playback before full generation)
- Model quantization (Q4_K_M or Q5_K_M for LLM)
- Warm model loading (keep models in memory)
- Audio pipeline optimization (minimal buffer sizes)

**Measurement:**
- Log timestamps at each pipeline stage
- Report P50, P95, P99 latencies in daily logs
- Alert if P95 exceeds maximum acceptable

---

### 3. Accuracy Requirements

**Target:** ≥95% intent recognition accuracy for supported commands.

| Component | Accuracy Target | Measurement Method |
|-----------|-----------------|-------------------|
| Wake word | ≥98% true positive, <1% false positive | Weekly sampling test |
| STT transcription | ≥95% WER (Word Error Rate) | Compare to manual transcripts |
| Intent classification | ≥95% correct intent | Tagged conversation review |
| Response quality | ≥90% user satisfaction | Implicit feedback (follow-ups, corrections) |

**Quality Assurance:**
- Maintain test utterance library (100+ phrases)
- Weekly automated accuracy benchmarks
- Log all corrections/clarifications as training signal

---

### 4. On-Demand Internet Connectivity

**Requirement:** Enhanced capabilities when connected, graceful operation when not.

#### Connectivity Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Offline** | No network detected | Local models only, full functionality |
| **Online - Local Preferred** | Network available, user preference | Use local models, cloud for overflow |
| **Online - Cloud Enhanced** | User request or complex query | Route to cloud APIs for higher quality |

#### Cloud Features (When Online)

| Feature | Cloud Service | Trigger |
|---------|---------------|---------|
| Complex reasoning | Claude API | "Think deeply about..." or query complexity score |
| Web search | Search API | "Search for...", "What's the latest..." |
| Real-time data | Weather/News APIs | Time-sensitive queries |
| Large context | Claude API | Conversation exceeds local context window |
| Voice cloning/custom TTS | Cloud TTS | User preference for specific voice |

#### Network Detection & Switching

```
On startup:
  1. Check network connectivity (ping test)
  2. Set initial mode based on result
  3. Display status indicator (LED or audio cue)

During operation:
  1. Monitor connectivity every 30 seconds
  2. Queue cloud requests if connection drops mid-query
  3. Retry queued requests when connection restores
  4. Never block user interaction for network issues
```

**User Controls:**
- "Ara, go offline" — Force offline mode
- "Ara, go online" — Enable cloud features
- "Ara, what mode are you in?" — Report current status

---

### 5. Conversation Logging & Daily Compilation

**Requirement:** All interactions logged and compiled into structured daily summaries.

#### Log Structure

**Per-Interaction Log (JSON Lines):**
```json
{
  "timestamp": "2026-01-12T14:32:15.123Z",
  "session_id": "ses_abc123",
  "interaction_id": "int_xyz789",
  "wake_word_confidence": 0.94,
  "audio_duration_ms": 2340,
  "transcript": "What time is my dentist appointment tomorrow",
  "transcript_confidence": 0.97,
  "intent": "calendar_query",
  "intent_confidence": 0.92,
  "entities": {
    "event_type": "dentist appointment",
    "time_reference": "tomorrow"
  },
  "response": "Your dentist appointment is tomorrow at 2:30 PM at Smile Dental on Main Street.",
  "response_source": "local_llm",
  "latency_ms": {
    "wake_word": 45,
    "stt": 412,
    "llm": 623,
    "tts": 198,
    "total": 1278
  },
  "mode": "offline",
  "error": null
}
```

**Daily Summary (Markdown):**
```markdown
# Ara Daily Log — 2026-01-12

## Summary Statistics
- Total interactions: 47
- Successful: 45 (95.7%)
- Errors: 2 (4.3%)
- Average latency: 1,342ms
- Mode breakdown: Offline 89%, Online 11%

## Top Intents
1. timer_set (12)
2. weather_query (8)
3. general_question (7)
4. reminder_create (6)

## Notable Interactions
### Complex Query Routed to Cloud
- **Time:** 14:32
- **Query:** "Explain the difference between RAFT and Paxos consensus algorithms"
- **Routing:** Local → Cloud (complexity threshold exceeded)
- **Response time:** 3.2s

### Error: STT Failure
- **Time:** 18:45
- **Audio duration:** 8.2s
- **Error:** Transcription timeout (audio too long)
- **Resolution:** Suggest shorter queries

## Action Items Extracted
- [ ] Dentist appointment tomorrow 2:30 PM
- [ ] Call mom this weekend
- [ ] Buy milk and eggs

## Insights
- Peak usage: 7:00-8:00 AM (morning routine)
- Most common correction: "Alexa" misheard as wake word
```

#### Storage & Retention

| Data Type | Location | Retention |
|-----------|----------|-----------|
| Raw audio | Not stored by default | Optional: 24 hours |
| Interaction logs | `~/ara/logs/YYYY-MM-DD.jsonl` | 90 days |
| Daily summaries | `~/ara/summaries/YYYY-MM-DD.md` | Indefinite |
| Aggregated metrics | `~/ara/metrics/monthly/YYYY-MM.json` | Indefinite |

#### Export & Integration

- **Format:** Markdown summaries, JSON raw logs
- **Sync:** Optional push to cloud storage (when online)
- **API:** Local HTTP endpoint for log queries
- **Integration:** Daily email digest (when online)

---

## System Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                           ARA SYSTEM                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐     │
│  │   MIC    │───▶│  WAKE    │───▶│   STT    │───▶│  INTENT  │     │
│  │  INPUT   │    │  WORD    │    │ (Whisper)│    │ PARSER   │     │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘     │
│                                         │              │           │
│                                         ▼              ▼           │
│                                  ┌─────────────────────────┐       │
│                                  │    ROUTER / ORCHESTRATOR │       │
│                                  │  (Online/Offline Logic)  │       │
│                                  └─────────────────────────┘       │
│                                         │              │           │
│                          ┌──────────────┴──────────────┐          │
│                          ▼                              ▼          │
│                   ┌──────────┐                   ┌──────────┐     │
│                   │  LOCAL   │                   │  CLOUD   │     │
│                   │   LLM    │                   │   API    │     │
│                   │(Llama 3) │                   │ (Claude) │     │
│                   └──────────┘                   └──────────┘     │
│                          │                              │          │
│                          └──────────────┬───────────────┘          │
│                                         ▼                          │
│                                  ┌──────────┐                      │
│                                  │   TTS    │                      │
│                                  │ (Piper)  │                      │
│                                  └──────────┘                      │
│                                         │                          │
│                                         ▼                          │
│  ┌──────────┐                    ┌──────────┐                      │
│  │  LOGGER  │◀───────────────────│  SPEAKER │                      │
│  │ (All I/O)│                    │  OUTPUT  │                      │
│  └──────────┘                    └──────────┘                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Stack

| Layer | Component | Technology |
|-------|-----------|------------|
| Hardware | Microphone | ReSpeaker USB or similar |
| Hardware | Speaker | 3.5mm or USB audio |
| Hardware | Compute | Raspberry Pi 4 (8GB) |
| OS | Base | Raspberry Pi OS Lite (64-bit) |
| Runtime | Python | 3.11+ with venv |
| Wake Word | Detection | Porcupine / OpenWakeWord |
| STT | Transcription | Whisper.cpp (ggml) |
| LLM | Local | llama.cpp + Llama 3.2 3B Q4 |
| LLM | Cloud | Anthropic Claude API |
| TTS | Synthesis | Piper TTS |
| Logging | Storage | SQLite + JSON files |
| API | Local | FastAPI (optional) |

---

## Hardware Requirements

### Minimum Specifications

| Component | Requirement | Notes |
|-----------|-------------|-------|
| Board | Raspberry Pi 4 | 8GB RAM strongly recommended |
| Storage | 64GB microSD | A2-rated for speed |
| Microphone | USB audio input | Far-field preferred |
| Speaker | Any audio output | 3.5mm or USB/Bluetooth |
| Power | 5V 3A USB-C | Official PSU recommended |
| Cooling | Passive or active | Required for sustained inference |

### Optional Enhancements

| Component | Purpose |
|-----------|---------|
| NVMe via USB 3.0 | Faster model loading |
| ReSpeaker 4-mic array | Better far-field pickup |
| LED ring | Visual feedback |
| Hardware button | Manual wake trigger |

---

## Model Selection

### Speech-to-Text (Whisper)

| Model | Size | Speed (Pi 4) | Accuracy | Recommended |
|-------|------|--------------|----------|-------------|
| tiny.en | 75MB | ~0.5s | Good | Development |
| base.en | 142MB | ~1.0s | Better | **Production** |
| small.en | 466MB | ~3.0s | Best | Cloud fallback |

### Language Model

| Model | Size | Speed (Pi 4) | Quality | Recommended |
|-------|------|--------------|---------|-------------|
| Phi-3 Mini 4K Q4 | 2.2GB | ~0.8s | Good | Fast queries |
| Llama 3.2 3B Q4 | 1.8GB | ~0.6s | Better | **Production** |
| Llama 3.2 3B Q5 | 2.1GB | ~0.9s | Best | Quality priority |

### Text-to-Speech (Piper)

| Voice | Size | Speed | Quality | Recommended |
|-------|------|-------|---------|-------------|
| en_US-lessac-medium | 75MB | Fast | Good | **Production** |
| en_US-amy-medium | 75MB | Fast | Good | Alternative |
| en_GB-alan-medium | 75MB | Fast | Good | British accent |

---

## Functional Requirements

### Core Commands (MVP)

| Category | Example Commands |
|----------|------------------|
| **Timers** | "Set a timer for 5 minutes" |
| **Alarms** | "Wake me up at 7 AM" |
| **Reminders** | "Remind me to call mom at 3 PM" |
| **Calculations** | "What's 15% of 84?" |
| **Conversions** | "How many cups in a liter?" |
| **Weather** | "What's the weather today?" (online) |
| **General Q&A** | "What's the capital of France?" |
| **System** | "Go offline", "What mode are you in?" |

### Extended Commands (Post-MVP)

| Category | Example Commands |
|----------|------------------|
| **Calendar** | "What's on my schedule tomorrow?" |
| **Notes** | "Add a note: buy groceries" |
| **Smart Home** | "Turn on the kitchen lights" |
| **Music** | "Play jazz music" |
| **Navigation** | "How long to downtown?" (online) |

---

## Non-Functional Requirements

### Performance

| Metric | Target |
|--------|--------|
| Cold boot to ready | < 30 seconds |
| Wake word to listening indicator | < 200ms |
| End-to-end response | < 2 seconds (P95) |
| Memory usage (idle) | < 2GB |
| Memory usage (active) | < 6GB |
| CPU usage (idle) | < 10% |

### Reliability

| Metric | Target |
|--------|--------|
| Uptime | 99.9% (excluding planned reboots) |
| Crash recovery | Auto-restart within 10 seconds |
| Data durability | No log loss on power failure |
| Graceful degradation | Function without any single component |

### Security

| Requirement | Implementation |
|-------------|----------------|
| No cloud by default | All processing local unless opted in |
| Encrypted storage | Logs encrypted at rest (optional) |
| No wake word audio storage | Audio discarded after processing |
| API key security | Environment variables, not config files |
| Network isolation | Firewall rules for cloud endpoints |

---

## User Experience

### Audio Feedback

| Event | Sound |
|-------|-------|
| Wake word detected | Short beep (listening) |
| Processing | Subtle ambient tone |
| Response ready | No sound (speech begins) |
| Error | Distinct error tone |
| Going online/offline | Mode-specific chime |

### Visual Feedback (Optional LED)

| State | LED Pattern |
|-------|-------------|
| Idle | Dim pulse (breathing) |
| Listening | Solid blue |
| Processing | Spinning animation |
| Speaking | Pulsing green |
| Error | Red flash |
| Offline | Amber indicator |

### Error Handling

| Error Type | User Message |
|------------|--------------|
| STT failure | "Sorry, I didn't catch that. Could you repeat?" |
| Intent unclear | "I'm not sure what you mean. Try rephrasing?" |
| LLM timeout | "I'm taking too long. Let me try a simpler answer." |
| Offline + cloud query | "I'm offline right now. I can answer that when connected." |

---

## Development Phases

### Phase 1: Foundation (Weeks 1-2)
- [ ] Hardware setup and OS configuration
- [ ] Wake word detection integration
- [ ] Basic STT pipeline (Whisper.cpp)
- [ ] Simple echo test (hear transcription)

### Phase 2: Local Intelligence (Weeks 3-4)
- [ ] Local LLM integration (llama.cpp)
- [ ] TTS integration (Piper)
- [ ] End-to-end voice loop
- [ ] Basic command handling

### Phase 3: Logging & Persistence (Weeks 5-6)
- [ ] Interaction logging system
- [ ] Daily summary generation
- [ ] Metrics collection
- [ ] Log export capabilities

### Phase 4: Cloud Integration (Weeks 7-8)
- [ ] Network detection
- [ ] Cloud API integration (Claude)
- [ ] Routing logic (local vs cloud)
- [ ] Mode switching commands

### Phase 5: Polish & Optimization (Weeks 9-10)
- [ ] Latency optimization
- [ ] Accuracy tuning
- [ ] Error handling refinement
- [ ] Audio feedback system

### Phase 6: Extended Features (Ongoing)
- [ ] Calendar integration
- [ ] Smart home connections
- [ ] Custom wake word training
- [ ] Multi-room support

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily active usage | 20+ interactions | Log count |
| User satisfaction | 90%+ successful queries | Error rate inverse |
| Response latency | <2s P95 | Logged timestamps |
| Uptime | 99.9% | System monitoring |
| Offline reliability | 100% core function | Weekly offline test |

---

## Open Questions

1. **Wake word selection:** "Ara" vs "Hey Ara" vs custom?
2. **Multi-user support:** Single user vs voice profiles?
3. **Persistent memory:** Should Ara remember context across days?
4. **Smart home protocol:** HomeKit, Home Assistant, or direct integrations?
5. **Car integration:** Bluetooth audio or hardwired?

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| STT | Speech-to-Text — Converting audio to text |
| TTS | Text-to-Speech — Converting text to audio |
| LLM | Large Language Model — AI for text generation |
| Wake Word | Activation phrase that starts listening |
| WER | Word Error Rate — STT accuracy metric |
| E2E | End-to-End — Complete pipeline measurement |
| Quantization | Model compression technique (Q4, Q5, etc.) |

---

## Appendix B: File Structure

```
~/ara/
├── README.md
├── requirements.txt
├── config/
│   ├── ara.yaml              # Main configuration
│   ├── models.yaml           # Model paths and settings
│   └── logging.yaml          # Log configuration
├── src/
│   ├── main.py               # Entry point
│   ├── wake_word/            # Wake word detection
│   ├── stt/                   # Speech-to-text
│   ├── llm/                   # Language model interface
│   ├── tts/                   # Text-to-speech
│   ├── router/                # Online/offline routing
│   └── logger/                # Logging system
├── models/                    # Downloaded models (gitignored)
│   ├── whisper/
│   ├── llama/
│   └── piper/
├── logs/                      # Daily interaction logs
│   └── 2026-01-12.jsonl
├── summaries/                 # Daily markdown summaries
│   └── 2026-01-12.md
├── tests/
│   ├── test_utterances/       # Audio test files
│   └── benchmarks/            # Performance tests
└── scripts/
    ├── setup.sh               # Initial setup
    ├── backup.sh              # Backup script
    └── daily_summary.py       # Summary generator
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-12 | Ammar Darkazanli | Initial draft |

---

*Ara Voice Assistant — Product Requirements Document*
