# Ara Voice Assistant — Raspberry Pi 4 (8GB) Setup Guide

**Ultra-Low Latency Local Voice Agent**

---

## Overview

This guide builds a fully offline, conversational voice assistant optimized for natural, low-latency interactions.

| Component | Model | Purpose | Target Latency |
|-----------|-------|---------|----------------|
| **STT** | faster-whisper small | Speech-to-Text | < 1.5s |
| **LLM** | Gemma 2 2B (Q4_K_M) | Response Generation | < 3s |
| **TTS** | Piper (medium voice) | Text-to-Speech | < 0.5s |
| **WEB** | DuckDuckGo (on-demand) | Internet Search | < 3s |

**Total end-to-end target:** 
- **Local queries:** 3-5 seconds
- **Internet queries:** 6-12 seconds

---

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| Raspberry Pi 4 | 8GB RAM (required) |
| microSD | 64GB+ Class A2 |
| Cooling | Active fan + heatsink (essential) |
| Microphone | ReSpeaker XVF3800 or USB mic |
| Speaker | 3.5mm or Bluetooth |
| Power | 5V/3A USB-C |

---

## Phase 1: System Preparation

### Step 1: Flash Raspberry Pi OS (64-bit)

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Select:
   - **Device:** Raspberry Pi 4
   - **OS:** Raspberry Pi OS (64-bit) Lite — *headless recommended for performance*
   - **Storage:** Your microSD card

3. Configure advanced options (gear icon):
   ```
   Hostname: ara
   Enable SSH: Yes
   Username: pi
   Password: [secure password]
   WiFi: [your network]
   Locale: America/Chicago
   ```

4. Flash and boot

### Step 2: Initial System Setup

```bash
# SSH into your Pi
ssh pi@ara.local

# Update system
sudo apt update && sudo apt full-upgrade -y

# Install essential dependencies
sudo apt install -y \
    git python3-pip python3-venv \
    portaudio19-dev libsndfile1 \
    ffmpeg libopenblas-dev \
    libasound2-dev alsa-utils \
    cmake build-essential curl

# Enable performance mode
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl disable ondemand

# Increase swap for model loading (temporary during init)
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=.*/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### Step 3: Configure Audio

```bash
# List audio devices
arecord -l
aplay -l

# Create ALSA config (adjust card numbers based on your hardware)
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type asym
    playback.pcm {
        type plug
        slave.pcm "hw:0,0"
    }
    capture.pcm {
        type plug
        slave.pcm "hw:1,0"
    }
}

ctl.!default {
    type hw
    card 0
}
EOF

# Test recording (5 seconds)
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 5 test.wav
aplay test.wav
```

---

## Phase 2: Create Project Environment

```bash
# Create project directory
mkdir -p ~/ara/{models,voices}
cd ~/ara

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools
```

---

## Phase 3: Install faster-whisper (STT)

faster-whisper uses CTranslate2 for optimized CPU inference—significantly faster than original Whisper.

```bash
cd ~/ara
source venv/bin/activate

# Install faster-whisper
pip install faster-whisper

# Download the small model (first run will auto-download, ~460MB)
# Or pre-download for offline use:
python3 << 'EOF'
from faster_whisper import WhisperModel

print("Downloading faster-whisper small model...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Model downloaded and ready!")
EOF
```

### Test faster-whisper

```bash
# Record a test phrase
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 5 ~/ara/test_stt.wav

# Test transcription
python3 << 'EOF'
from faster_whisper import WhisperModel
import time

model = WhisperModel("small", device="cpu", compute_type="int8")

start = time.time()
segments, info = model.transcribe("test_stt.wav", beam_size=1, language="en")
text = " ".join([seg.text for seg in segments])
elapsed = time.time() - start

print(f"Transcription: {text}")
print(f"Time: {elapsed:.2f}s")
EOF
```

**Expected performance:** 1-2 seconds for 5 seconds of audio.

---

## Phase 4: Install Gemma 2 2B via Ollama (LLM)

Ollama provides the easiest setup with optimized inference.

### Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Enable and start service
sudo systemctl enable ollama
sudo systemctl start ollama

# Verify installation
ollama --version
```

### Download Gemma 2 2B

```bash
# Pull the quantized model (~1.6GB)
ollama pull gemma2:2b

# Test the model
ollama run gemma2:2b "Hello! Respond in one sentence."
```

### Optimize Ollama for Low Latency

```bash
# Create optimized Modelfile for voice assistant
cat > ~/ara/Modelfile << 'EOF'
FROM gemma2:2b

# Optimize for voice assistant responses
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 100
PARAMETER repeat_penalty 1.1

SYSTEM """You are Ara, a helpful voice assistant. Keep responses brief, 
conversational, and under 2 sentences. Be natural and friendly.
Never use markdown, lists, or formatting—speak naturally."""
EOF

# Create custom model
ollama create ara-voice -f ~/ara/Modelfile

# Test the optimized model
ollama run ara-voice "What's the weather like?"
```

### Test LLM Latency

```bash
python3 << 'EOF'
import requests
import time

def query_llm(prompt):
    start = time.time()
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "ara-voice",
            "prompt": prompt,
            "stream": False
        }
    )
    elapsed = time.time() - start
    return response.json()["response"], elapsed

text, latency = query_llm("What time is it?")
print(f"Response: {text}")
print(f"Latency: {latency:.2f}s")
EOF
```

**Expected performance:** 2-4 seconds for short responses.

---

## Phase 5: Install Piper TTS

Piper is optimized for Raspberry Pi and provides natural-sounding speech with minimal latency.

### Install Piper

```bash
cd ~/ara
source venv/bin/activate

# Install piper-tts
pip install piper-tts
```

### Download Voice Model

```bash
cd ~/ara/voices

# Download a high-quality English voice (Amy - medium quality, good balance)
# Available voices: https://huggingface.co/rhasspy/piper-voices

# Option 1: Amy (US English, medium)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

# Option 2: Lessac (US English, medium - slightly faster)
# wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
# wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

### Test Piper TTS

```bash
# Test from command line
echo "Hello! I am Ara, your voice assistant." | \
    piper --model ~/ara/voices/en_US-amy-medium.onnx --output_file test_tts.wav

aplay test_tts.wav

# Test latency
python3 << 'EOF'
from piper import PiperVoice
import wave
import time

voice = PiperVoice.load("/home/pi/ara/voices/en_US-amy-medium.onnx")

text = "Hello! How can I help you today?"
start = time.time()

with wave.open("latency_test.wav", "wb") as wav:
    voice.synthesize(text, wav)

elapsed = time.time() - start
print(f"TTS latency: {elapsed:.2f}s for {len(text)} characters")
EOF

aplay latency_test.wav
```

**Expected performance:** < 0.5 seconds for short sentences.

---

## Phase 6: Build the Voice Agent

### Install Additional Dependencies

```bash
cd ~/ara
source venv/bin/activate

pip install sounddevice numpy scipy webrtcvad requests duckduckgo-search
```

---

## Phase 6.5: Configure Internet Access (On-Demand)

Ara can access the internet when you say trigger phrases like:
- "Ara **with internet**, check the news"
- "Ara **search for** best restaurants nearby"  
- "Ara **look up** the weather in Austin"
- "Ara **what's the latest** on AI"

### Test DuckDuckGo Search

```bash
python3 << 'EOF'
from duckduckgo_search import DDGS

# Test web search
print("Testing web search...")
results = DDGS().text("Raspberry Pi 5 release", max_results=3)
for r in results:
    print(f"  - {r['title']}")

# Test news search
print("\nTesting news search...")
news = DDGS().news("technology", max_results=3)
for n in news:
    print(f"  - {n['title']}")
EOF
```

---

### Create the Main Ara Script

```bash
cat > ~/ara/ara.py << 'SCRIPT'
#!/usr/bin/env python3
"""
Ara Voice Assistant
Ultra-low latency local voice agent for Raspberry Pi 4

Components:
- STT: faster-whisper small (int8)
- LLM: Gemma 2 2B via Ollama
- TTS: Piper (medium voice)
- WEB: DuckDuckGo search (on-demand)
"""

import os
import sys
import time
import wave
import queue
import re
import tempfile
import subprocess
import numpy as np
import sounddevice as sd
import requests
from faster_whisper import WhisperModel
from piper import PiperVoice

# Internet search (optional, graceful fallback)
try:
    from duckduckgo_search import DDGS
    INTERNET_AVAILABLE = True
except ImportError:
    INTERNET_AVAILABLE = False
    print("⚠️  duckduckgo-search not installed. Internet features disabled.")

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    # Audio settings
    "sample_rate": 16000,
    "channels": 1,
    "chunk_duration": 0.5,  # seconds per audio chunk
    
    # Voice Activity Detection
    "silence_threshold": 500,  # RMS threshold
    "silence_duration": 1.0,   # seconds of silence to end recording
    "max_recording": 15.0,     # maximum recording length
    
    # Model paths
    "whisper_model": "small",
    "whisper_compute": "int8",  # int8 for speed on CPU
    "piper_voice": os.path.expanduser("~/ara/voices/en_US-amy-medium.onnx"),
    
    # Ollama settings
    "ollama_url": "http://localhost:11434/api/generate",
    "ollama_model": "ara-voice",
    "max_tokens": 100,
    "max_tokens_with_context": 150,  # More tokens when summarizing web results
    
    # Wake word (simple keyword detection)
    "wake_word": "ara",
    "wake_word_timeout": 300,  # seconds before requiring wake word again
    
    # Internet search settings
    "max_search_results": 3,
    "max_news_results": 5,
}

# Internet trigger phrases
INTERNET_TRIGGERS = [
    "with internet",
    "search for",
    "search the web",
    "look up",
    "find online",
    "google",
    "check online",
    "what's the latest",
    "latest news",
    "current news",
    "today's news",
    "check the news",
    "news about",
    "headlines",
]

NEWS_TRIGGERS = [
    "news",
    "headlines",
    "latest",
    "current events",
    "what's happening",
]

# ============================================================================
# VOICE ASSISTANT CLASS
# ============================================================================

class AraVoiceAssistant:
    def __init__(self):
        self.running = True
        self.last_interaction = 0
        self.audio_queue = queue.Queue()
        
        print("🚀 Initializing Ara Voice Assistant...")
        self._load_models()
        
        if INTERNET_AVAILABLE:
            print("🌐 Internet search: Enabled")
        else:
            print("🌐 Internet search: Disabled")
        
        print("✅ Ara is ready! Say 'Ara' to begin.\n")
        print("💡 Tip: Say 'Ara with internet, check the news' for web access\n")
    
    def _load_models(self):
        """Load all AI models"""
        # Load faster-whisper
        print("📝 Loading speech recognition (faster-whisper small)...")
        start = time.time()
        self.whisper = WhisperModel(
            CONFIG["whisper_model"],
            device="cpu",
            compute_type=CONFIG["whisper_compute"]
        )
        print(f"   Loaded in {time.time() - start:.1f}s")
        
        # Load Piper TTS
        print("🔊 Loading text-to-speech (Piper)...")
        start = time.time()
        self.tts = PiperVoice.load(CONFIG["piper_voice"])
        print(f"   Loaded in {time.time() - start:.1f}s")
        
        # Test Ollama connection
        print("🧠 Connecting to LLM (Ollama)...")
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            models = [m["name"] for m in response.json().get("models", [])]
            if CONFIG["ollama_model"] not in models and "ara-voice:latest" not in models:
                print(f"   ⚠️  Model '{CONFIG['ollama_model']}' not found. Using gemma2:2b")
                CONFIG["ollama_model"] = "gemma2:2b"
            print("   Connected!")
        except Exception as e:
            print(f"   ❌ Ollama error: {e}")
            sys.exit(1)
    
    def speak(self, text):
        """Convert text to speech and play"""
        if not text.strip():
            return
        
        print(f"🔊 Ara: {text}")
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            # Generate speech
            with wave.open(temp_path, "wb") as wav:
                self.tts.synthesize(text, wav)
            
            # Play audio
            subprocess.run(
                ["aplay", "-q", temp_path],
                check=True,
                capture_output=True
            )
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def record_audio(self):
        """Record audio until silence detected"""
        print("🎤 Listening...")
        
        frames = []
        silence_start = None
        recording_start = time.time()
        
        chunk_samples = int(CONFIG["sample_rate"] * CONFIG["chunk_duration"])
        
        def callback(indata, frame_count, time_info, status):
            self.audio_queue.put(indata.copy())
        
        with sd.InputStream(
            samplerate=CONFIG["sample_rate"],
            channels=CONFIG["channels"],
            dtype=np.int16,
            blocksize=chunk_samples,
            callback=callback
        ):
            while True:
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    frames.append(audio_chunk)
                    
                    # Calculate RMS for silence detection
                    rms = np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2))
                    
                    if rms < CONFIG["silence_threshold"]:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > CONFIG["silence_duration"]:
                            break
                    else:
                        silence_start = None
                    
                    # Check max recording time
                    if time.time() - recording_start > CONFIG["max_recording"]:
                        break
                        
                except queue.Empty:
                    continue
        
        if not frames:
            return None
        
        return np.concatenate(frames)
    
    def transcribe(self, audio_data):
        """Transcribe audio using faster-whisper"""
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            with wave.open(temp_path, "wb") as wav:
                wav.setnchannels(CONFIG["channels"])
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(CONFIG["sample_rate"])
                wav.writeframes(audio_data.tobytes())
        
        try:
            start = time.time()
            segments, _ = self.whisper.transcribe(
                temp_path,
                beam_size=1,  # Faster, single beam
                language="en",
                vad_filter=True,  # Filter silence
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            text = " ".join([seg.text for seg in segments]).strip()
            elapsed = time.time() - start
            
            print(f"   📝 Heard: \"{text}\" ({elapsed:.1f}s)")
            return text
        finally:
            os.unlink(temp_path)
    
    # ========================================================================
    # INTERNET SEARCH FUNCTIONS
    # ========================================================================
    
    def needs_internet(self, text):
        """Check if the query requires internet access"""
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in INTERNET_TRIGGERS)
    
    def is_news_query(self, text):
        """Check if this is a news-specific query"""
        text_lower = text.lower()
        return any(trigger in text_lower for trigger in NEWS_TRIGGERS)
    
    def extract_search_query(self, text):
        """Extract the actual search query from the command"""
        text_lower = text.lower()
        
        # Remove wake word
        text_lower = text_lower.replace(CONFIG["wake_word"], "").strip()
        
        # Remove trigger phrases
        for trigger in INTERNET_TRIGGERS:
            text_lower = text_lower.replace(trigger, "").strip()
        
        # Clean up common filler words at the start
        fillers = ["about", "for", "on", "the", "what is", "what are", "who is"]
        for filler in fillers:
            if text_lower.startswith(filler + " "):
                text_lower = text_lower[len(filler):].strip()
        
        return text_lower if text_lower else "general news"
    
    def search_web(self, query):
        """Perform a web search using DuckDuckGo"""
        if not INTERNET_AVAILABLE:
            return None
        
        print(f"   🌐 Searching web for: {query}")
        
        try:
            results = DDGS().text(
                query,
                max_results=CONFIG["max_search_results"],
                region="us-en"
            )
            return results
        except Exception as e:
            print(f"   ❌ Search error: {e}")
            return None
    
    def search_news(self, query=None):
        """Fetch news using DuckDuckGo"""
        if not INTERNET_AVAILABLE:
            return None
        
        search_term = query if query else "top news today"
        print(f"   📰 Fetching news: {search_term}")
        
        try:
            news = DDGS().news(
                search_term,
                max_results=CONFIG["max_news_results"],
                region="us-en",
                timelimit="d"  # Past day
            )
            return news
        except Exception as e:
            print(f"   ❌ News error: {e}")
            return None
    
    def format_search_results(self, results, is_news=False):
        """Format search results for the LLM to summarize"""
        if not results:
            return None
        
        formatted = []
        for i, r in enumerate(results, 1):
            if is_news:
                title = r.get("title", "No title")
                body = r.get("body", "")[:200]
                source = r.get("source", "Unknown")
                formatted.append(f"{i}. [{source}] {title}: {body}")
            else:
                title = r.get("title", "No title")
                body = r.get("body", "")[:200]
                formatted.append(f"{i}. {title}: {body}")
        
        return "\n".join(formatted)
    
    # ========================================================================
    # LLM FUNCTIONS
    # ========================================================================
    
    def query_llm(self, prompt, context=None):
        """Send query to Ollama LLM"""
        start = time.time()
        
        # Build the full prompt
        if context:
            full_prompt = f"""Based on the following information from the internet:

{context}

Please provide a brief, conversational summary answering: {prompt}

Keep your response to 2-3 sentences, suitable for voice output."""
            max_tokens = CONFIG["max_tokens_with_context"]
        else:
            full_prompt = prompt
            max_tokens = CONFIG["max_tokens"]
        
        try:
            response = requests.post(
                CONFIG["ollama_url"],
                json={
                    "model": CONFIG["ollama_model"],
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    }
                },
                timeout=30
            )
            
            result = response.json()["response"].strip()
            elapsed = time.time() - start
            print(f"   🧠 Thought for {elapsed:.1f}s")
            return result
            
        except Exception as e:
            print(f"   ❌ LLM error: {e}")
            return "Sorry, I had trouble thinking about that."
    
    def check_wake_word(self, text):
        """Check if wake word was spoken"""
        text_lower = text.lower()
        return CONFIG["wake_word"] in text_lower
    
    def process_command(self, text):
        """Process a voice command"""
        # Remove wake word from query
        query = text.lower().replace(CONFIG["wake_word"], "").strip()
        
        if not query:
            return "Yes? How can I help you?"
        
        # ====================================================================
        # CHECK FOR INTERNET REQUEST
        # ====================================================================
        if self.needs_internet(text):
            search_query = self.extract_search_query(text)
            
            if self.is_news_query(text):
                # News search
                self.speak("Let me check the latest news.")
                results = self.search_news(search_query)
                
                if results:
                    context = self.format_search_results(results, is_news=True)
                    return self.query_llm(
                        f"Summarize these news headlines about {search_query}",
                        context=context
                    )
                else:
                    return "Sorry, I couldn't fetch the news right now."
            else:
                # General web search
                self.speak("Searching the web.")
                results = self.search_web(search_query)
                
                if results:
                    context = self.format_search_results(results, is_news=False)
                    return self.query_llm(
                        f"Answer this question based on web results: {search_query}",
                        context=context
                    )
                else:
                    return "Sorry, I couldn't search the web right now."
        
        # ====================================================================
        # LOCAL COMMANDS (No internet needed)
        # ====================================================================
        
        # Time
        if "time" in query:
            from datetime import datetime
            now = datetime.now()
            return f"It's {now.strftime('%I:%M %p')}."
        
        # Date
        if "date" in query:
            from datetime import datetime
            now = datetime.now()
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        
        # Help
        if "help" in query or "what can you do" in query:
            return ("I can answer questions, tell you the time and date, "
                    "and search the internet. Just say 'with internet' "
                    "before your question for web searches.")
        
        # ====================================================================
        # DEFAULT: Send to local LLM
        # ====================================================================
        return self.query_llm(query)
    
    def run(self):
        """Main conversation loop"""
        self.speak("Hello! I'm Ara. Say my name when you need me.")
        
        waiting_for_wake = True
        
        while self.running:
            try:
                audio = self.record_audio()
                if audio is None:
                    continue
                
                text = self.transcribe(audio)
                if not text:
                    continue
                
                # Check for wake word or active conversation
                is_wake = self.check_wake_word(text)
                in_conversation = (time.time() - self.last_interaction) < CONFIG["wake_word_timeout"]
                
                if is_wake or (in_conversation and not waiting_for_wake):
                    self.last_interaction = time.time()
                    waiting_for_wake = False
                    
                    # Get response
                    response = self.process_command(text)
                    
                    # Speak response
                    self.speak(response)
                else:
                    # Reset conversation state after timeout
                    if not in_conversation:
                        waiting_for_wake = True
                    print("   (Waiting for wake word 'Ara'...)")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
                continue

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    assistant = AraVoiceAssistant()
    assistant.run()
SCRIPT

chmod +x ~/ara/ara.py
```

---

## Phase 7: Performance Optimization

### Create Optimized Startup Script

```bash
cat > ~/ara/start_ara.sh << 'EOF'
#!/bin/bash
# Ara Voice Assistant Startup Script

cd ~/ara
source venv/bin/activate

# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1

# Pre-warm the LLM (keep in memory)
echo "Pre-warming LLM..."
curl -s http://localhost:11434/api/generate -d '{"model":"ara-voice","prompt":"hello","stream":false}' > /dev/null

echo "Starting Ara..."
python3 ara.py
EOF

chmod +x ~/ara/start_ara.sh
```

### Enable Auto-Start on Boot

```bash
# Create systemd service
sudo tee /etc/systemd/system/ara.service << 'EOF'
[Unit]
Description=Ara Voice Assistant
After=network.target sound.target ollama.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ara
Environment="PATH=/home/pi/ara/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/pi/ara/venv/bin/python3 /home/pi/ara/ara.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable ara.service
```

---

## Phase 8: Latency Benchmarks

### Run Benchmark Script

```bash
cat > ~/ara/benchmark.py << 'EOF'
#!/usr/bin/env python3
"""Benchmark each component of the voice pipeline"""

import time
import wave
import tempfile
import requests
from faster_whisper import WhisperModel
from piper import PiperVoice

print("=" * 60)
print("ARA VOICE ASSISTANT - LATENCY BENCHMARK")
print("=" * 60)

# Test STT
print("\n📝 Testing STT (faster-whisper small)...")
model = WhisperModel("small", device="cpu", compute_type="int8")

# Create 3-second test audio
sample_rate = 16000
duration = 3
samples = [0] * (sample_rate * duration)

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    temp_path = f.name
    with wave.open(temp_path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(samples))

start = time.time()
segments, _ = model.transcribe(temp_path, beam_size=1, language="en")
list(segments)  # Consume generator
stt_time = time.time() - start
print(f"   STT latency: {stt_time:.2f}s")

# Test LLM
print("\n🧠 Testing LLM (Gemma 2 2B via Ollama)...")
prompts = [
    "Hello",
    "What is the capital of France?",
    "Tell me a short joke"
]

for prompt in prompts:
    start = time.time()
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "ara-voice", "prompt": prompt, "stream": False}
    )
    llm_time = time.time() - start
    tokens = len(response.json()["response"].split())
    print(f"   '{prompt[:20]}...' → {llm_time:.2f}s ({tokens} words)")

# Test TTS
print("\n🔊 Testing TTS (Piper)...")
voice = PiperVoice.load("/home/pi/ara/voices/en_US-amy-medium.onnx")

test_phrases = [
    "Hello.",
    "The weather is nice today.",
    "I can help you with many different tasks."
]

for phrase in test_phrases:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        start = time.time()
        with wave.open(f.name, "wb") as wav:
            voice.synthesize(phrase, wav)
        tts_time = time.time() - start
        print(f"   '{phrase[:25]}...' → {tts_time:.2f}s ({len(phrase)} chars)")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"STT (3s audio):     ~{stt_time:.1f}s")
print(f"LLM (short query):  ~2-4s")
print(f"TTS (short phrase): ~0.3-0.5s")
print(f"Total pipeline:     ~3-6s end-to-end")
print("=" * 60)
EOF

chmod +x ~/ara/benchmark.py
source ~/ara/venv/bin/activate
python3 ~/ara/benchmark.py
```

---

## Internet Voice Commands

### Trigger Phrases

Ara listens for these phrases to activate internet search:

| Phrase | Example |
|--------|---------|
| "with internet" | "Ara **with internet**, what's the weather in Austin?" |
| "search for" | "Ara **search for** best pizza near me" |
| "look up" | "Ara **look up** the capital of France" |
| "check the news" | "Ara **check the news** about technology" |
| "what's the latest" | "Ara **what's the latest** on AI?" |
| "headlines" | "Ara, give me today's **headlines**" |

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                    INTERNET FLOW                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  "Ara with internet, check the news about Tesla"            │
│                          │                                   │
│                          ▼                                   │
│              ┌─────────────────────┐                        │
│              │  Detect trigger:    │                        │
│              │  "with internet"    │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  Extract query:     │                        │
│              │  "Tesla"            │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  DuckDuckGo News    │──── No API key needed! │
│              │  Search             │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  LLM summarizes     │                        │
│              │  results            │                        │
│              └──────────┬──────────┘                        │
│                         │                                    │
│                         ▼                                    │
│              ┌─────────────────────┐                        │
│              │  Piper speaks       │                        │
│              │  summary            │                        │
│              └─────────────────────┘                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Example Interactions

**News Query:**
```
You: "Ara with internet, check the news about artificial intelligence"
Ara: "Let me check the latest news."
     [Fetches 5 news articles from DuckDuckGo]
Ara: "Here's the latest on AI. OpenAI announced a new model update, 
     Google is expanding its Gemini capabilities, and there's growing 
     discussion about AI regulation in Europe."
```

**Web Search:**
```
You: "Ara, search for how to make sourdough bread"
Ara: "Searching the web."
     [Fetches 3 web results]
Ara: "To make sourdough, you'll need a starter, flour, water, and salt. 
     The process takes about 24 hours including proofing time. 
     King Arthur Baking has a great beginner recipe."
```

**Offline Query (no trigger phrase):**
```
You: "Ara, what time is it?"
Ara: "It's 3:45 PM."
     [No internet used - answered locally]
```

---

## Expected Performance

### Local Queries (No Internet)

| Stage | Latency | Notes |
|-------|---------|-------|
| Audio capture | ~1-2s | User speaking |
| STT (faster-whisper) | 1.0-1.5s | 3-5s of speech |
| LLM (Gemma 2 2B) | 2-4s | Short responses |
| TTS (Piper) | 0.3-0.5s | Response audio |
| **Total** | **3-6s** | End-to-end |

### Internet Queries

| Stage | Latency | Notes |
|-------|---------|-------|
| Audio capture | ~1-2s | User speaking |
| STT (faster-whisper) | 1.0-1.5s | 3-5s of speech |
| Web search (DuckDuckGo) | 1-3s | Depends on connection |
| LLM summarization | 3-5s | Processing search results |
| TTS (Piper) | 0.5-1s | Longer response |
| **Total** | **6-12s** | End-to-end with internet |

---

## Troubleshooting

### Audio Issues

```bash
# Check audio devices
arecord -l
aplay -l

# Test microphone
arecord -D plughw:1,0 -f S16_LE -r 16000 -c 1 -d 3 test.wav
aplay test.wav

# Adjust microphone gain
alsamixer
```

### Memory Issues

```bash
# Monitor memory
htop

# Clear cache
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'

# Check Ollama memory
ollama ps
```

### Ollama Not Responding

```bash
# Restart Ollama
sudo systemctl restart ollama

# Check logs
journalctl -u ollama -f

# Test API
curl http://localhost:11434/api/tags
```

### Internet Search Issues

```bash
# Test internet connectivity
ping -c 3 google.com

# Test DuckDuckGo search
python3 << 'EOF'
from duckduckgo_search import DDGS
try:
    results = DDGS().text("test query", max_results=1)
    print("✅ DuckDuckGo working:", results[0]["title"])
except Exception as e:
    print("❌ Error:", e)
EOF

# If rate limited, wait a few minutes or check your connection
```

---

## Optional Enhancements

### Add Streaming TTS (Lower Perceived Latency)

```python
# In ara.py, modify speak() for streaming:
def speak_streaming(self, text):
    """Stream TTS for lower perceived latency"""
    import subprocess
    
    process = subprocess.Popen(
        ["piper", "--model", CONFIG["piper_voice"], "--output-raw"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    
    aplay = subprocess.Popen(
        ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-q"],
        stdin=process.stdout
    )
    
    process.stdin.write(text.encode())
    process.stdin.close()
    aplay.wait()
```

### Add LLM Streaming (First-Word Latency)

```python
import json

def query_llm_streaming(self, prompt):
    """Stream LLM responses for faster first-word latency"""
    response = requests.post(
        CONFIG["ollama_url"],
        json={"model": CONFIG["ollama_model"], "prompt": prompt, "stream": True},
        stream=True
    )
    
    full_response = ""
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            chunk = data.get("response", "")
            full_response += chunk
            # Could trigger TTS on sentence boundaries here
    
    return full_response
```

### Use faster-whisper tiny for Even Lower Latency

```python
# Trade accuracy for speed
CONFIG["whisper_model"] = "tiny"  # ~75MB, faster but less accurate
```

---

## Model Alternatives

| Component | Default | Alternative | Trade-off |
|-----------|---------|-------------|-----------|
| STT | faster-whisper small | faster-whisper tiny | Faster, less accurate |
| LLM | Gemma 2 2B | TinyLlama 1.1B | Much faster, less capable |
| LLM | Gemma 2 2B | Qwen2.5 0.5B | Faster, simpler responses |
| TTS | Piper amy-medium | Piper lessac-low | Faster, lower quality |

---

## Quick Reference

```bash
# Start Ara manually
cd ~/ara && source venv/bin/activate && ./start_ara.sh

# Start as service
sudo systemctl start ara

# View logs
journalctl -u ara -f

# Run benchmark
cd ~/ara && source venv/bin/activate && python3 benchmark.py

# Update models
ollama pull gemma2:2b

# Test internet search
python3 -c "from duckduckgo_search import DDGS; print(DDGS().news('tech', max_results=1))"

# Check system resources
htop
```

### Voice Command Cheat Sheet

| Command | Example |
|---------|---------|
| Wake word | "Ara" |
| Time | "Ara, what time is it?" |
| Date | "Ara, what's today's date?" |
| Local question | "Ara, tell me a joke" |
| Web search | "Ara **with internet**, search for..." |
| News | "Ara, **check the news** about..." |
| Help | "Ara, what can you do?" |

---

*Built for Ammar's Ara Voice Assistant Project — January 2026*
