# Internal API Contracts: Ara Voice Assistant

**Date**: 2026-01-12
**Branch**: `001-ara-voice-assistant`

This document defines the interfaces between internal modules. All modules communicate through these contracts, enabling independent testing and replacement.

---

## 1. Audio Module

### AudioCapture Interface

```python
from typing import Protocol, Iterator
from dataclasses import dataclass

@dataclass
class AudioChunk:
    """Raw audio data chunk."""
    data: bytes
    sample_rate: int  # Hz
    channels: int
    sample_width: int  # bytes per sample
    timestamp_ms: int

class AudioCapture(Protocol):
    """Interface for audio input capture."""

    def start(self) -> None:
        """Start capturing audio from input device."""
        ...

    def stop(self) -> None:
        """Stop capturing audio."""
        ...

    def read(self, frames: int) -> AudioChunk:
        """Read specified number of frames from buffer."""
        ...

    def stream(self) -> Iterator[AudioChunk]:
        """Yield audio chunks continuously."""
        ...

    @property
    def is_active(self) -> bool:
        """Return True if capture is active."""
        ...
```

### AudioPlayback Interface

```python
class AudioPlayback(Protocol):
    """Interface for audio output playback."""

    def play(self, audio: bytes, sample_rate: int) -> None:
        """Play audio data. Blocks until complete."""
        ...

    def play_async(self, audio: bytes, sample_rate: int) -> None:
        """Play audio data without blocking."""
        ...

    def stop(self) -> None:
        """Stop current playback."""
        ...

    def play_tone(self, frequency: int, duration_ms: int) -> None:
        """Play a simple tone (for feedback)."""
        ...

    @property
    def is_playing(self) -> bool:
        """Return True if audio is currently playing."""
        ...
```

---

## 2. Wake Word Module

### WakeWordDetector Interface

```python
from dataclasses import dataclass

@dataclass
class WakeWordResult:
    """Result of wake word detection."""
    detected: bool
    confidence: float  # 0.0 to 1.0
    keyword: str  # The wake word detected
    timestamp_ms: int

class WakeWordDetector(Protocol):
    """Interface for wake word detection."""

    def initialize(self, keywords: list[str], sensitivity: float) -> None:
        """Initialize detector with keywords and sensitivity."""
        ...

    def process(self, audio: AudioChunk) -> WakeWordResult:
        """Process audio chunk for wake word detection."""
        ...

    def cleanup(self) -> None:
        """Release resources."""
        ...
```

---

## 3. STT Module

### Transcriber Interface

```python
from dataclasses import dataclass
from typing import Iterator

@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription."""
    text: str
    confidence: float  # 0.0 to 1.0
    language: str  # Detected language code
    duration_ms: int  # Audio duration processed
    segments: list[dict]  # Word-level timestamps (optional)

@dataclass
class PartialTranscription:
    """Partial result during streaming transcription."""
    text: str
    is_final: bool

class Transcriber(Protocol):
    """Interface for speech-to-text transcription."""

    def transcribe(self, audio: bytes, sample_rate: int) -> TranscriptionResult:
        """Transcribe audio buffer to text."""
        ...

    def transcribe_stream(
        self, audio_stream: Iterator[AudioChunk]
    ) -> Iterator[PartialTranscription]:
        """Stream transcription results as audio arrives."""
        ...

    def set_language(self, language: str) -> None:
        """Set expected language (e.g., 'en' for English)."""
        ...
```

---

## 4. LLM Module

### LanguageModel Interface

```python
from dataclasses import dataclass
from typing import Iterator

@dataclass
class LLMResponse:
    """Response from language model."""
    text: str
    tokens_used: int
    model: str
    latency_ms: int

@dataclass
class StreamToken:
    """Single token in streaming response."""
    token: str
    is_complete: bool

class LanguageModel(Protocol):
    """Interface for language model inference."""

    def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate response for prompt."""
        ...

    def generate_stream(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.7,
    ) -> Iterator[StreamToken]:
        """Stream response tokens as they're generated."""
        ...

    def set_system_prompt(self, prompt: str) -> None:
        """Set system prompt for conversation context."""
        ...

    def clear_context(self) -> None:
        """Clear conversation history."""
        ...
```

---

## 5. TTS Module

### Synthesizer Interface

```python
from dataclasses import dataclass

@dataclass
class SynthesisResult:
    """Result of text-to-speech synthesis."""
    audio: bytes
    sample_rate: int
    duration_ms: int
    latency_ms: int

class Synthesizer(Protocol):
    """Interface for text-to-speech synthesis."""

    def synthesize(self, text: str) -> SynthesisResult:
        """Convert text to speech audio."""
        ...

    def set_voice(self, voice_id: str) -> None:
        """Set the voice to use for synthesis."""
        ...

    def set_speed(self, speed: float) -> None:
        """Set speech speed (1.0 = normal)."""
        ...

    def get_available_voices(self) -> list[str]:
        """Return list of available voice IDs."""
        ...
```

---

## 6. Router Module

### Intent Classifier

```python
from dataclasses import dataclass
from enum import Enum

class IntentType(Enum):
    """Supported intent types."""
    TIMER_SET = "timer_set"
    TIMER_QUERY = "timer_query"
    TIMER_CANCEL = "timer_cancel"
    REMINDER_SET = "reminder_set"
    REMINDER_QUERY = "reminder_query"
    GENERAL_QUESTION = "general_question"
    WEB_SEARCH = "web_search"
    WEATHER_QUERY = "weather_query"
    MODE_QUERY = "mode_query"
    MODE_SWITCH = "mode_switch"
    UNKNOWN = "unknown"

@dataclass
class Intent:
    """Classified intent from user input."""
    type: IntentType
    confidence: float
    entities: dict  # Extracted entities (e.g., duration, time)
    requires_cloud: bool  # Whether intent needs internet

class IntentClassifier(Protocol):
    """Interface for intent classification."""

    def classify(self, text: str) -> Intent:
        """Classify user intent from transcript."""
        ...
```

### Mode Manager

```python
from enum import Enum

class OperationMode(Enum):
    """System operation modes."""
    OFFLINE = "offline"
    ONLINE_LOCAL_PREFERRED = "online_local"
    ONLINE_CLOUD_ENHANCED = "online_cloud"

class ModeManager(Protocol):
    """Interface for mode management."""

    def get_mode(self) -> OperationMode:
        """Get current operation mode."""
        ...

    def set_mode(self, mode: OperationMode) -> bool:
        """Set operation mode. Returns success status."""
        ...

    def is_network_available(self) -> bool:
        """Check if network is currently available."""
        ...
```

### Orchestrator

```python
from dataclasses import dataclass

@dataclass
class QueryResult:
    """Result of processing a user query."""
    response_text: str
    response_source: str  # "local_llm", "cloud_api", "system"
    intent: Intent
    latency_ms: dict  # Component-level latencies

class Orchestrator(Protocol):
    """Interface for query orchestration."""

    def process_query(self, transcript: str) -> QueryResult:
        """Process user query and return response."""
        ...

    def handle_command(self, intent: Intent) -> QueryResult:
        """Handle system commands (timers, mode, etc.)."""
        ...
```

---

## 7. Commands Module

### Timer Manager

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TimerInfo:
    """Timer information for queries."""
    id: str
    name: Optional[str]
    remaining_seconds: int
    status: str

class TimerManager(Protocol):
    """Interface for timer management."""

    def create_timer(
        self,
        duration_seconds: int,
        name: Optional[str] = None,
        interaction_id: str = None,
    ) -> str:
        """Create a new timer. Returns timer ID."""
        ...

    def cancel_timer(self, timer_id: str) -> bool:
        """Cancel a timer. Returns success status."""
        ...

    def get_active_timers(self) -> list[TimerInfo]:
        """Get all active timers."""
        ...

    def get_timer(self, timer_id: str) -> Optional[TimerInfo]:
        """Get specific timer info."""
        ...

    def on_timer_expired(self, callback: callable) -> None:
        """Register callback for timer expiration."""
        ...
```

### Reminder Manager

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class ReminderInfo:
    """Reminder information for queries."""
    id: str
    message: str
    remind_at: datetime
    status: str

class ReminderManager(Protocol):
    """Interface for reminder management."""

    def create_reminder(
        self,
        message: str,
        remind_at: datetime,
        recurrence: Optional[str] = None,
        interaction_id: str = None,
    ) -> str:
        """Create a new reminder. Returns reminder ID."""
        ...

    def cancel_reminder(self, reminder_id: str) -> bool:
        """Cancel a reminder. Returns success status."""
        ...

    def get_pending_reminders(self) -> list[ReminderInfo]:
        """Get all pending reminders."""
        ...

    def on_reminder_due(self, callback: callable) -> None:
        """Register callback for reminder due."""
        ...
```

---

## 8. Logger Module

### InteractionLogger

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class InteractionLog:
    """Complete interaction log entry."""
    interaction_id: str
    session_id: str
    timestamp: datetime
    device_id: str
    wake_word_confidence: float
    audio_duration_ms: int
    transcript: str
    transcript_confidence: float
    intent: str
    intent_confidence: float
    entities: dict
    response: str
    response_source: str
    latency_ms: dict
    mode: str
    error: Optional[str]

class InteractionLogger(Protocol):
    """Interface for interaction logging."""

    def log(self, entry: InteractionLog) -> None:
        """Log an interaction."""
        ...

    def get_today_interactions(self) -> list[InteractionLog]:
        """Get all interactions from today."""
        ...

    def get_interactions_by_date(
        self, date: datetime.date
    ) -> list[InteractionLog]:
        """Get interactions for a specific date."""
        ...
```

### SummaryGenerator

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class DailySummaryData:
    """Data for daily summary."""
    date: date
    device_id: str
    total_interactions: int
    successful_interactions: int
    error_count: int
    avg_latency_ms: int
    p95_latency_ms: int
    mode_breakdown: dict
    top_intents: list[dict]
    action_items: list[str]

class SummaryGenerator(Protocol):
    """Interface for daily summary generation."""

    def generate(self, target_date: date) -> DailySummaryData:
        """Generate summary for a specific date."""
        ...

    def export_markdown(self, summary: DailySummaryData) -> str:
        """Export summary as Markdown string."""
        ...

    def save_summary(self, summary: DailySummaryData) -> None:
        """Save summary to file."""
        ...
```

---

## 9. Feedback Module

### AudioFeedback

```python
from enum import Enum

class FeedbackType(Enum):
    """Types of audio feedback."""
    WAKE_WORD_DETECTED = "wake"
    PROCESSING = "processing"
    ERROR = "error"
    MODE_CHANGE = "mode_change"
    TIMER_ALERT = "timer_alert"
    REMINDER_ALERT = "reminder_alert"

class AudioFeedback(Protocol):
    """Interface for audio feedback sounds."""

    def play(self, feedback_type: FeedbackType) -> None:
        """Play feedback sound for event type."""
        ...

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable feedback sounds."""
        ...
```

---

## Module Dependency Graph

```
                    ┌─────────────┐
                    │   Config    │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│     Audio     │  │   Wake Word   │  │   Feedback    │
│ Capture/Play  │  │   Detector    │  │    Sounds     │
└───────┬───────┘  └───────┬───────┘  └───────────────┘
        │                  │
        ▼                  ▼
┌───────────────┐  ┌───────────────┐
│      STT      │  │    Router     │
│  Transcriber  │  │ Orchestrator  │
└───────┬───────┘  └───────┬───────┘
        │                  │
        │          ┌───────┴───────┐
        │          │               │
        ▼          ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│      LLM      │  │   Commands    │  │    Logger     │
│LanguageModel  │  │ Timer/Remind  │  │  Interaction  │
└───────┬───────┘  └───────────────┘  └───────────────┘
        │
        ▼
┌───────────────┐
│      TTS      │
│  Synthesizer  │
└───────────────┘
```

---

## Error Handling Contract

All modules MUST follow this error handling pattern:

```python
from enum import Enum
from dataclasses import dataclass

class ErrorSeverity(Enum):
    """Error severity levels."""
    RECOVERABLE = "recoverable"  # Can continue with degraded functionality
    FATAL = "fatal"  # Module cannot continue

@dataclass
class ModuleError:
    """Standardized module error."""
    module: str  # Module name (e.g., "stt", "llm")
    operation: str  # Operation that failed
    message: str  # Human-readable message
    severity: ErrorSeverity
    user_message: str  # Message to speak to user
    details: dict  # Additional context for debugging

# All module methods should raise ModuleError on failure
# Recoverable errors should be caught and handled
# Fatal errors should propagate to main loop
```
