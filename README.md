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

## Setup Instructions

### macOS Setup (Development)

#### Prerequisites

1. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. **Install Python 3.11+**:
   ```bash
   brew install python@3.12
   ```

3. **Install system dependencies**:
   ```bash
   brew install portaudio ffmpeg
   ```

4. **Install Ollama** (for LLM):
   ```bash
   brew install ollama
   ```

#### Project Setup

```bash
# Clone the repository
git clone https://github.com/adarkazanli/RPVA.git
cd RPVA

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e ".[dev]"

# Download the LLM model
ollama pull llama3.2:3b

# Verify installation
PYTHONPATH=src python -m ara --dry-run --profile dev
```

#### Running on macOS

```bash
# Start Ollama service (in a separate terminal)
ollama serve

# Run the voice assistant
source venv/bin/activate
PYTHONPATH=src python -m ara --profile dev
```

---

### Raspberry Pi Setup (Production)

#### Prerequisites

- Raspberry Pi 4 Model B (8GB RAM recommended)
- 64GB+ microSD card (Class A2 for speed)
- Active cooling (fan + heatsink) - **essential for sustained operation**
- USB microphone or ReSpeaker array
- Speaker (3.5mm jack or Bluetooth)
- Raspberry Pi OS (64-bit) - Bookworm or newer

#### Step 1: Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select **Raspberry Pi OS (64-bit)** - Desktop or Lite
3. Click the gear icon to pre-configure:
   - Set hostname: `ara`
   - Enable SSH
   - Set username/password
   - Configure WiFi (if needed)
4. Flash to microSD card and boot

#### Step 2: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    portaudio19-dev \
    libportaudio2 \
    libasound2-dev \
    libsndfile1 \
    ffmpeg \
    git \
    curl

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

#### Step 3: Audio Configuration

```bash
# List audio devices
arecord -l  # Input devices
aplay -l    # Output devices

# Test microphone (Ctrl+C to stop)
arecord -d 5 -f cd test.wav
aplay test.wav

# If needed, set default audio device in ~/.asoundrc:
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type asym
    playback.pcm "plughw:Headphones,0"
    capture.pcm "plughw:USB,0"
}
ctl.!default {
    type hw
    card Headphones
}
EOF

# Adjust volume
alsamixer
```

#### Step 4: Project Installation

```bash
# Clone the repository
git clone https://github.com/adarkazanli/RPVA.git
cd RPVA

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -e .

# Download models
ollama pull llama3.2:3b

# Verify installation
PYTHONPATH=src python -m ara --dry-run --profile prod
```

#### Step 5: Running the Assistant

```bash
# Start Ollama service
sudo systemctl start ollama

# Run the assistant
source venv/bin/activate
PYTHONPATH=src python -m ara --profile prod
```

#### Step 6: Auto-Start on Boot (Optional)

Create a systemd service:

```bash
sudo tee /etc/systemd/system/ara.service << 'EOF'
[Unit]
Description=Ara Voice Assistant
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/RPVA
Environment=PYTHONPATH=/home/pi/RPVA/src
ExecStart=/home/pi/RPVA/venv/bin/python -m ara --profile prod
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable ara
sudo systemctl start ara

# Check status
sudo systemctl status ara
journalctl -u ara -f  # View logs
```

---

### Troubleshooting

#### Audio Issues

```bash
# Check if audio devices are detected
arecord -l
aplay -l

# Test with specific device
arecord -D plughw:1,0 -d 5 test.wav
aplay -D plughw:0,0 test.wav

# Check PulseAudio (if installed)
pactl list sources short
pactl list sinks short
```

#### Ollama Issues

```bash
# Check Ollama status
systemctl status ollama

# Restart Ollama
sudo systemctl restart ollama

# Check if model is downloaded
ollama list

# Pull model again if needed
ollama pull llama3.2:3b
```

#### Performance Issues on Raspberry Pi

```bash
# Check CPU temperature (should be < 80°C)
vcgencmd measure_temp

# Check memory usage
free -h

# Check CPU throttling
vcgencmd get_throttled  # 0x0 means no throttling

# If overheating, ensure active cooling is working
```

#### Python/Dependency Issues

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -e ".[dev]" --force-reinstall

# Check Python version (needs 3.11+)
python --version
```

---

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
