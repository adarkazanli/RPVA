# RPVA - Raspberry Pi Voice Assistant

Ultra-low latency, fully offline voice assistant optimized for Raspberry Pi 4.

## Features

- **Fully Offline**: Core functionality works without internet
- **Low Latency**: 3-6 second end-to-end response time
- **Privacy-First**: All processing happens locally
- **Natural Voice**: High-quality text-to-speech output
- **Optional Web Search**: On-demand internet access with trigger phrases

## Architecture

| Component | Technology | Purpose | Target Latency |
|-----------|------------|---------|----------------|
| **STT** | faster-whisper (small) | Speech-to-Text | < 1.5s |
| **LLM** | Gemma 2 2B via Ollama | Response Generation | < 4s |
| **TTS** | Piper (medium voice) | Text-to-Speech | < 0.5s |
| **Search** | DuckDuckGo | Optional Web Search | < 3s |

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| Raspberry Pi | 4 Model B, 8GB RAM |
| Storage | 64GB+ microSD (Class A2) |
| Cooling | Active fan + heatsink (essential) |
| Microphone | USB mic or ReSpeaker |
| Speaker | 3.5mm or Bluetooth |
| Power | 5V/3A USB-C |

## Quick Start

See the full [Setup Guide](ara-voice-assistant-pi4-setup.md) for detailed instructions.

```bash
# Clone the repository
git clone https://github.com/adarkazanli/RPVA.git
cd RPVA

# Follow the setup guide for:
# 1. System preparation
# 2. Audio configuration
# 3. Model installation (faster-whisper, Ollama, Piper)
# 4. Running the assistant
```

## Voice Commands

| Command Type | Example |
|--------------|---------|
| Wake word | "Ara" |
| Time | "Ara, what time is it?" |
| Date | "Ara, what's today's date?" |
| General question | "Ara, tell me a joke" |
| Web search | "Ara **with internet**, search for..." |
| News | "Ara, **check the news** about..." |

## Performance Targets

| Query Type | Target Latency |
|------------|----------------|
| Local queries | 3-6 seconds |
| Internet queries | 6-12 seconds |

## Project Structure

```
RPVA/
├── README.md                          # This file
├── ara-voice-assistant-pi4-setup.md   # Complete setup guide
├── src/ara/                           # Main source code
│   ├── audio/                         # Audio capture/playback
│   ├── config/                        # Configuration management
│   ├── llm/                           # Language model interface
│   ├── router/                        # Pipeline orchestration
│   ├── stt/                           # Speech-to-text
│   ├── tts/                           # Text-to-speech
│   └── wake_word/                     # Wake word detection
├── tests/                             # Test suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── fixtures/                      # Test data
├── config/                            # Configuration profiles
│   ├── base.yaml                      # Base configuration
│   ├── dev.yaml                       # Development settings
│   └── prod.yaml                      # Production settings
└── .specify/                          # Project specifications
    ├── memory/
    │   └── constitution.md            # Development principles
    └── templates/                     # Spec templates
```

## Cross-Platform Development

Ara supports development and testing on multiple platforms:

| Platform | Development | Production | CI/CD |
|----------|-------------|------------|-------|
| macOS (Apple Silicon) | Primary | - | Supported |
| macOS (Intel) | Supported | - | Supported |
| Linux (x86_64) | Supported | Supported | Primary |
| Raspberry Pi 4 | - | Primary | - |

### GPU Acceleration

Ara automatically detects and uses available hardware acceleration:

- **Apple Silicon**: Metal Performance Shaders (MPS)
- **NVIDIA GPU**: CUDA
- **CPU**: Fallback for all platforms

### Running Tests

```bash
# Run all tests
PYTHONPATH=src pytest tests/ -v

# Run only unit tests
PYTHONPATH=src pytest tests/unit -v

# Run integration tests (may require mocks)
PYTHONPATH=src pytest tests/integration -v

# Run with mock audio (for CI/headless environments)
python -m ara --mock-audio --dry-run --profile dev
```

### CI/CD Pipeline

The project uses GitHub Actions for continuous integration:

- **Platforms tested**: Ubuntu, macOS
- **Python versions**: 3.11, 3.12
- **Checks**: Linting (ruff), type checking (mypy), unit tests, integration tests

All tests run with mock audio components, so no real audio hardware is required.

## Development Principles

This project follows a constitution-driven development approach. Key principles:

1. **Performance-First**: All components must meet latency targets
2. **Offline-First**: No cloud dependencies in core pipeline
3. **Modularity**: Separate, replaceable components
4. **Simplicity**: YAGNI - minimum required complexity
5. **Test-Driven**: Tests before implementation
6. **Benchmark-Driven**: Measure performance on target hardware
7. **Documentation-First**: Update docs with code changes

See [.specify/memory/constitution.md](.specify/memory/constitution.md) for full details.

## License

Private project.

---

*Built for Raspberry Pi 4 - January 2026*
