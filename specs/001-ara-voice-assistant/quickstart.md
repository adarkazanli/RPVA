# Quickstart Guide: Ara Voice Assistant

**Date**: 2026-01-12
**Branch**: `001-ara-voice-assistant`

This guide helps developers set up their local environment and run Ara.

---

## Prerequisites

### macOS

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 ffmpeg portaudio

# Verify installations
python3.11 --version  # Should be 3.11+
ffmpeg -version
```

### Ubuntu/Debian (Laptop or Pi)

```bash
# Update package list
sudo apt update

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
    ffmpeg portaudio19-dev libasound2-dev

# Verify installations
python3.11 --version  # Should be 3.11+
ffmpeg -version
```

### Raspberry Pi 4 (Additional)

```bash
# Enable I2S audio (for ReSpeaker)
sudo raspi-config  # Interface Options > I2S > Enable

# Install ALSA utilities
sudo apt install -y alsa-utils

# Test audio
arecord -l  # List recording devices
aplay -l    # List playback devices
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/adarkazanli/RPVA.git
cd RPVA
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download Models

```bash
# Download all models (2-3 GB total)
./scripts/download_models.sh

# Or download individually:
./scripts/download_models.sh --whisper base.en
./scripts/download_models.sh --llm llama-3.2-3b
./scripts/download_models.sh --tts en_US-lessac-medium
```

### 5. Install Ollama (for LLM)

**macOS:**
```bash
brew install ollama
ollama serve &  # Start Ollama server
ollama pull llama3.2:3b  # Download model
```

**Linux/Pi:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
systemctl start ollama  # Start as service
ollama pull llama3.2:3b  # Download model
```

---

## Configuration

### Development Profile (Laptop)

Create or verify `config/dev.yaml`:

```yaml
extends: base.yaml

ara:
  log_level: DEBUG
  audio:
    input_device: "default"
    output_device: "default"
    sample_rate: 16000
  models:
    whisper_acceleration: "metal"  # Use "cpu" if no GPU
    llm_acceleration: "metal"      # Use "cpu" if no GPU
  testing:
    mock_audio: true  # Enable for testing without mic
```

### Production Profile (Pi 4)

Create or verify `config/prod.yaml`:

```yaml
extends: base.yaml

ara:
  log_level: INFO
  audio:
    input_device: "respeaker"  # Or your USB mic name
    output_device: "default"
    sample_rate: 16000
  models:
    whisper_acceleration: "cpu"
    llm_acceleration: "cpu"
  testing:
    mock_audio: false
```

---

## Running Ara

### Development Mode (Laptop)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with dev config
python -m ara --config config/dev.yaml
```

### Production Mode (Pi 4)

```bash
# Activate virtual environment
source venv/bin/activate

# Run with prod config
python -m ara --config config/prod.yaml
```

### With Mock Audio (Testing)

```bash
# Run with mock audio from test fixtures
python -m ara --config config/dev.yaml --mock-audio tests/fixtures/audio/

# Run a specific test utterance
python -m ara --config config/dev.yaml --test-utterance "what_time_is_it"
```

---

## Testing

### Run All Tests

```bash
# Unit and integration tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Benchmark tests (requires Pi 4 for accurate results)
pytest tests/benchmark/ -v --benchmark-only
```

### Run Linting

```bash
# Format code
ruff format src/ tests/

# Check for issues
ruff check src/ tests/
mypy src/
```

---

## Common Development Tasks

### Add a New Voice Command

1. Define intent in `src/router/intent.py`
2. Add handler in appropriate module (`src/commands/`)
3. Write unit test in `tests/unit/`
4. Add test audio fixture in `tests/fixtures/audio/`
5. Update documentation

### Test STT Accuracy

```bash
# Run STT benchmark with test utterances
python scripts/benchmark.py --component stt --fixtures tests/fixtures/audio/
```

### Test E2E Latency

```bash
# Run full pipeline benchmark
python scripts/benchmark.py --component e2e --iterations 10
```

### Generate Daily Summary Manually

```bash
python scripts/daily_summary.py --date 2026-01-12
```

---

## Troubleshooting

### "No audio input device found"

**macOS:**
```bash
# List audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"
```

**Linux:**
```bash
# List ALSA devices
arecord -l

# Check PulseAudio
pactl list sources short
```

### "Ollama connection refused"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### "Model not found"

```bash
# List downloaded models
ollama list

# Pull missing model
ollama pull llama3.2:3b
```

### High Latency on Pi 4

1. Ensure CPU governor is set to "performance":
   ```bash
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```

2. Close other applications to free RAM

3. Check for thermal throttling:
   ```bash
   vcgencmd measure_temp
   vcgencmd get_throttled
   ```

### Wake Word Not Detecting

1. Check microphone levels:
   ```bash
   arecord -d 5 test.wav && aplay test.wav
   ```

2. Adjust sensitivity in config:
   ```yaml
   ara:
     wake_word:
       sensitivity: 0.6  # Increase for more sensitivity (0.3-0.9)
   ```

---

## Project Structure Reference

```
RPVA/
├── src/                    # Source code
│   ├── __main__.py        # Entry point
│   ├── audio/             # Audio capture/playback
│   ├── wake_word/         # Wake word detection
│   ├── stt/               # Speech-to-text
│   ├── llm/               # Language model
│   ├── tts/               # Text-to-speech
│   ├── router/            # Intent classification, orchestration
│   ├── commands/          # Timer, reminder handlers
│   ├── logger/            # Interaction logging
│   └── feedback/          # Audio feedback sounds
├── config/                 # Configuration files
├── models/                 # Downloaded models (gitignored)
├── logs/                   # Interaction logs (gitignored)
├── summaries/              # Daily summaries
├── tests/                  # Test suite
│   ├── unit/
│   ├── integration/
│   ├── benchmark/
│   └── fixtures/
├── scripts/                # Utility scripts
└── specs/                  # Feature specifications
```

---

## Next Steps

1. **Read the spec**: `specs/001-ara-voice-assistant/spec.md`
2. **Review the data model**: `specs/001-ara-voice-assistant/data-model.md`
3. **Understand the contracts**: `specs/001-ara-voice-assistant/contracts/`
4. **Start with Phase 1**: Wake word + STT integration
5. **Run benchmarks**: Validate latency targets on target hardware

---

## Getting Help

- **Documentation**: See `ara-voice-assistant-pi4-setup.md` for detailed setup
- **Issues**: Report bugs at https://github.com/adarkazanli/RPVA/issues
- **Constitution**: Review development principles in `.specify/memory/constitution.md`
