# RPVA - Raspberry Pi Voice Assistant

Ultra-low latency, fully offline voice assistant optimized for Raspberry Pi 4.

## Quick Start

```bash
# 1. Install dependencies and activate virtual environment
pip install -e ".[dev]"
source venv/bin/activate

# 2. Start Ollama (in a separate terminal)
ollama serve

# 3. Download models (Whisper STT + Piper TTS)
./scripts/download_models.sh

# 4. Set up API keys
#    - Picovoice: Get a free key at https://console.picovoice.ai/
#    - Tavily (optional): Get a free key at https://tavily.com/ for web search
cat > .env << 'EOF'
PICOVOICE_ACCESS_KEY=your_picovoice_key_here
TAVILY_API_KEY=your_tavily_key_here
EOF

# 5. Run Ara
PYTHONPATH=src python -m ara --profile dev
```

**Usage:** Say **"porcupine"** (wake word), then ask your question. Ara will transcribe, process, and speak the response.

> **Note:** The default wake word is "porcupine" (a built-in Porcupine keyword). To use a custom wake word like "Ara", train a model at [Picovoice Console](https://console.picovoice.ai/).

## Features

- **Fully Offline**: Core functionality works without internet
- **Low Latency**: 3-6 second end-to-end response time
- **Privacy-First**: All processing happens locally
- **Natural Voice**: High-quality text-to-speech output
- **Optional Web Search**: On-demand internet access with trigger phrases
- **Voice Notes**: Capture notes with automatic entity extraction (people, topics, locations)
- **Time Tracking**: Track activity duration with start/stop commands
- **Daily/Weekly Digests**: Get summaries of how you spend your time

## Web Search Setup (Tavily)

Ara uses [Tavily](https://tavily.com/) for real-time web search, optimized for AI assistants with clean, summarized results.

### Getting Your API Key

1. Visit [https://tavily.com/](https://tavily.com/)
2. Sign up for a free account (1,000 searches/month free tier)
3. Copy your API key from the dashboard

### Configuration

Add your Tavily API key to the `.env` file:

```bash
# Add to .env file
echo "TAVILY_API_KEY=tvly-your-api-key-here" >> .env
```

Or set it as an environment variable:

```bash
export TAVILY_API_KEY=tvly-your-api-key-here
```

### Usage

Trigger web search with these **keywords**:

| Trigger Phrase | Example |
|----------------|---------|
| `with internet` | "Porcupine, **with internet**, what's the weather in Tokyo?" |
| `search online` | "Porcupine, **search online** for best restaurants nearby" |
| `look up` | "Porcupine, **look up** the latest iPhone specs" |
| `check the news` | "Porcupine, **check the news** about the stock market" |
| `current` / `latest` | "Porcupine, what's the **current** price of Bitcoin?" |

### Features

- **AI-Optimized Results**: Tavily returns clean, summarized content perfect for voice responses
- **Fast Response**: Typical search latency < 2 seconds
- **Graceful Fallback**: If no API key is set, Ara falls back to a mock client (returns "search unavailable")
- **Smart Routing**: Only queries with trigger phrases use web search; others stay fully offline

> **Note:** Web search is optional. Without a Tavily API key, Ara works fully offline for all other features.

## Architecture

| Component | Technology | Purpose | Target Latency |
|-----------|------------|---------|----------------|
| **STT** | faster-whisper (small) | Speech-to-Text | < 1.5s |
| **LLM** | Gemma 2 2B via Ollama | Response Generation | < 4s |
| **TTS** | Piper (medium voice) | Text-to-Speech | < 0.5s |
| **Search** | Tavily API | Optional Web Search | < 2s |

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

#### Download Models

```bash
# Download Whisper (STT) and Piper (TTS) models
./scripts/download_models.sh
```

#### Set Up Wake Word Detection

Get a free Picovoice API key at [https://console.picovoice.ai/](https://console.picovoice.ai/) and add it to your environment:

```bash
echo "PICOVOICE_ACCESS_KEY=your_key_here" > .env
```

#### Running on macOS

```bash
# Start Ollama service (in a separate terminal)
ollama serve

# Run the voice assistant
source venv/bin/activate
PYTHONPATH=src python -m ara --profile dev

# Say "porcupine" then ask a question!
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

### Docker Setup (MongoDB)

Ara uses MongoDB for persistent storage of notes, activities, and interaction history. Docker is the recommended way to run MongoDB.

#### Installing Docker on macOS

1. **Download Docker Desktop**:
   - Visit [https://www.docker.com/products/docker-desktop/](https://www.docker.com/products/docker-desktop/)
   - Download Docker Desktop for Mac (Apple Silicon or Intel)

2. **Install and Start**:
   ```bash
   # After installing, start Docker Desktop from Applications
   # Verify installation
   docker --version
   docker-compose --version
   ```

3. **Run MongoDB**:
   ```bash
   cd RPVA/docker

   # For Apple Silicon (M1/M2/M3) - use the default ARM64 image
   docker-compose up -d

   # For Intel Mac - update the image first
   sed -i '' 's|arm64v8/mongo:4.4.18|mongo:4.4|' docker-compose.yml
   docker-compose up -d
   ```

#### Installing Docker on Raspberry Pi

1. **Install Docker using the convenience script**:
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Add your user to docker group (avoid using sudo)
   sudo usermod -aG docker $USER

   # Log out and back in, then verify
   docker --version
   ```

2. **Install Docker Compose**:
   ```bash
   # Install docker-compose plugin
   sudo apt install docker-compose-plugin -y

   # Or install standalone docker-compose
   sudo pip3 install docker-compose

   # Verify
   docker compose version
   ```

3. **Run MongoDB**:
   ```bash
   cd ~/RPVA/docker

   # The default image (arm64v8/mongo:4.4.18) works on Raspberry Pi 4
   docker-compose up -d

   # Verify MongoDB is running
   docker ps
   docker logs ara_mongodb
   ```

#### Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start MongoDB in background |
| `docker-compose down` | Stop MongoDB |
| `docker-compose logs -f` | View MongoDB logs |
| `docker ps` | List running containers |
| `docker exec -it ara_mongodb mongo` | Connect to MongoDB shell |

#### MongoDB Connection

Once MongoDB is running, Ara connects automatically. The default connection string:

```
mongodb://localhost:27017/ara
```

To verify the connection:

```bash
# Test MongoDB connection
docker exec -it ara_mongodb mongo --eval "db.runCommand('ping')"

# Or using mongosh (if installed locally)
mongosh "mongodb://localhost:27017/ara" --eval "db.stats()"
```

#### Auto-Start MongoDB on Boot (Raspberry Pi)

```bash
# Enable Docker to start on boot
sudo systemctl enable docker

# The container has restart: unless-stopped, so it will auto-start
# To verify after reboot:
docker ps
```

#### Troubleshooting Docker

```bash
# Check if Docker daemon is running
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Check container logs
docker logs ara_mongodb

# Remove and recreate container (data persists in volume)
docker-compose down
docker-compose up -d

# Check disk space (MongoDB needs space)
df -h

# Check memory usage
docker stats ara_mongodb
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

### General Commands

| Command Type | Example | Keywords |
|--------------|---------|----------|
| Wake word | "Porcupine" (default) or custom trained keyword | - |
| Time | "[wake word], what time is it?" | - |
| Date | "[wake word], what's today's date?" | - |
| General question | "[wake word], what is the capital of France?" | - |
| Web search | "[wake word] **with internet**, search for..." | `with internet`, `search online` |
| News | "[wake word], **check the news** about..." | `check the news`, `latest news` |

### Voice Notes

Capture notes with automatic extraction of people, topics, and locations.

| Action | Example | Keywords |
|--------|---------|----------|
| Capture note | "[wake word], **remember that** I met with John about the project" | `remember that`, `note that`, `make a note` |
| Query notes | "[wake word], **what did I say about** the meeting?" | `what did I say about`, `notes about`, `find notes` |

### Time Tracking

Track how you spend your time with start/stop activity commands.

| Action | Example | Keywords |
|--------|---------|----------|
| Start activity | "[wake word], **starting** work on the report" | `starting`, `start`, `begin`, `working on` |
| Stop activity | "[wake word], **done with** the report" | `done with`, `finished`, `stopped`, `completed` |
| Daily digest | "[wake word], **how did I spend my time today?**" | `how did I spend`, `today's summary`, `daily digest` |
| Weekly digest | "[wake word], **give me a weekly summary**" | `weekly summary`, `this week`, `weekly insights` |

### Categories

Activities and notes are auto-categorized into:

| Category | Keywords that trigger it |
|----------|-------------------------|
| **Work** | meeting, call, project, deadline, client, coding, presentation |
| **Health** | workout, exercise, gym, running, yoga, meditation, doctor |
| **Errands** | groceries, shopping, pharmacy, bank, appointment, pickup |
| **Personal** | family, friend, dinner, movie, reading, relax, vacation |

> **Tip:** After saying the wake word, wait for a brief moment, then speak your question clearly. Ara will automatically detect when you've finished speaking.

---

## Note-Taking & Time Tracking

### How It Works

**Voice Notes** automatically extract entities from your speech:
- **People**: Names mentioned (e.g., "I met with **John** and **Sarah**")
- **Topics**: Subjects discussed (e.g., "about the **quarterly budget**")
- **Locations**: Places mentioned (e.g., "at the **downtown office**")

**Time Tracking** monitors activity duration:
- Say "**starting** [activity]" to begin tracking
- Say "**done with** [activity]" to stop and calculate duration
- Only one activity can be active at a time (starting a new one auto-closes the previous)
- Activities auto-close after 4 hours if you forget to stop them

### Example Workflow

```
You: "Porcupine, starting work on the quarterly report"
Ara: "Started tracking: work on the quarterly report"

... 2 hours later ...

You: "Porcupine, done with the report"
Ara: "Completed: work on the quarterly report. Duration: 2 hours 5 minutes"

... end of day ...

You: "Porcupine, how did I spend my time today?"
Ara: "Today you spent 2 hours on work, 45 minutes on health, and 30 minutes on errands.
      Total: 3 hours and 15 minutes."
```

### Insights & Patterns

Ask for weekly insights to understand your time allocation:

```
You: "Porcupine, give me a weekly summary"
Ara: "This week you tracked 18 hours total. You spent 12 hours on work and 4 hours on health.
      Tuesday was your busiest day with 5 hours."
```

---

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
│   ├── wake_word/                     # Wake word detection
│   ├── notes/                         # Voice notes & entity extraction
│   ├── activities/                    # Activity duration tracking
│   └── digest/                        # Daily/weekly time summaries
├── tests/                             # Test suite
│   ├── unit/                          # Unit tests
│   ├── integration/                   # Integration tests
│   └── fixtures/                      # Test data
├── config/                            # Configuration profiles
│   ├── base.yaml                      # Base configuration
│   ├── dev.yaml                       # Development settings
│   └── prod.yaml                      # Production settings
├── docker/                            # Docker configuration
│   └── docker-compose.yml             # MongoDB container setup
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
