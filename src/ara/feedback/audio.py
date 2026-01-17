"""Audio feedback implementation.

Provides auditory feedback using:
- Pre-recorded WAV files (beeps, chimes)
- Generated tones (fallback)
"""

import math
import struct
import wave
from pathlib import Path
from typing import TYPE_CHECKING

from . import FeedbackType

if TYPE_CHECKING:
    from ..audio.playback import AudioPlayback
    from ..config import FeedbackConfig


# Default frequencies for generated tones (Hz)
TONE_FREQUENCIES: dict[FeedbackType, int] = {
    FeedbackType.WAKE_WORD_DETECTED: 880,  # A5 - pleasant attention getter
    FeedbackType.PROCESSING: 440,  # A4 - neutral
    FeedbackType.ERROR: 220,  # A3 - low, indicates problem
    FeedbackType.MODE_CHANGE: 660,  # E5 - distinctive
    FeedbackType.TIMER_ALERT: 1000,  # High, attention-grabbing
    FeedbackType.REMINDER_ALERT: 800,  # Slightly lower than timer
    FeedbackType.SUCCESS: 523,  # C5 - positive
    FeedbackType.INTERRUPT_ACKNOWLEDGED: 200,  # Low "boop" - distinct from wake beep
    FeedbackType.THINKING: 523,  # C5 - pleasant chime while waiting for LLM
    FeedbackType.RESPONSE_COMPLETE: 440,  # A4 - neutral long beep at end
}

# Default durations for generated tones (ms)
TONE_DURATIONS: dict[FeedbackType, int] = {
    FeedbackType.WAKE_WORD_DETECTED: 100,
    FeedbackType.PROCESSING: 50,
    FeedbackType.ERROR: 300,
    FeedbackType.MODE_CHANGE: 150,
    FeedbackType.TIMER_ALERT: 500,
    FeedbackType.REMINDER_ALERT: 400,
    FeedbackType.SUCCESS: 200,
    FeedbackType.INTERRUPT_ACKNOWLEDGED: 100,  # Quick, doesn't delay response
    FeedbackType.THINKING: 150,  # Short chime, loops every 800ms
    FeedbackType.RESPONSE_COMPLETE: 400,  # Long beep to signal end of interaction
}


def generate_tone(frequency: int, duration_ms: int, sample_rate: int = 22050) -> bytes:
    """Generate a simple sine wave tone.

    Args:
        frequency: Tone frequency in Hz
        duration_ms: Duration in milliseconds
        sample_rate: Sample rate in Hz

    Returns:
        Raw PCM audio bytes (16-bit mono)
    """
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate
        # Apply envelope to avoid clicks
        envelope = 1.0
        attack_samples = int(sample_rate * 0.01)  # 10ms attack
        release_samples = int(sample_rate * 0.01)  # 10ms release

        if i < attack_samples:
            envelope = i / attack_samples
        elif i > num_samples - release_samples:
            envelope = (num_samples - i) / release_samples

        sample = int(32767 * 0.5 * envelope * math.sin(2 * math.pi * frequency * t))
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def load_wav_file(path: Path) -> tuple[bytes, int]:
    """Load a WAV file and return audio data and sample rate.

    Args:
        path: Path to WAV file

    Returns:
        Tuple of (audio_bytes, sample_rate)

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"WAV file not found: {path}")

    with wave.open(str(path), "rb") as wf:
        sample_rate = wf.getframerate()
        audio_data = wf.readframes(wf.getnframes())

    return audio_data, sample_rate


class SoundFeedback:
    """Audio feedback using sound files or generated tones.

    Attempts to load sound files from configured directory,
    falls back to generated tones if files not found.
    """

    def __init__(
        self,
        playback: "AudioPlayback",
        config: "FeedbackConfig | None" = None,
        sounds_dir: Path | None = None,
    ) -> None:
        """Initialize audio feedback.

        Args:
            playback: AudioPlayback instance for playing sounds
            config: Feedback configuration
            sounds_dir: Directory containing sound files
        """
        self._playback = playback
        self._enabled = True
        self._sounds_dir = sounds_dir
        self._sound_cache: dict[FeedbackType, tuple[bytes, int]] = {}

        # Map feedback types to sound files
        self._sound_files: dict[FeedbackType, str] = {
            FeedbackType.WAKE_WORD_DETECTED: "beep.wav",
            FeedbackType.ERROR: "error.wav",
            FeedbackType.MODE_CHANGE: "chime.wav",
            FeedbackType.TIMER_ALERT: "timer_alert.wav",
            FeedbackType.REMINDER_ALERT: "reminder_alert.wav",
            FeedbackType.SUCCESS: "success.wav",
            FeedbackType.PROCESSING: "beep.wav",
        }

        if config is not None:
            self._enabled = config.audio_enabled
            # Override sound files from config
            for key, filename in config.sounds.items():
                try:
                    feedback_type = FeedbackType(key)
                    self._sound_files[feedback_type] = filename
                except ValueError:
                    pass  # Ignore unknown feedback types

        # Preload sounds
        self._preload_sounds()

    def _preload_sounds(self) -> None:
        """Preload sound files into cache."""
        if self._sounds_dir is None:
            return

        for feedback_type, filename in self._sound_files.items():
            path = self._sounds_dir / filename
            if path.exists():
                try:
                    audio_data, sample_rate = load_wav_file(path)
                    self._sound_cache[feedback_type] = (audio_data, sample_rate)
                except Exception:
                    pass  # Will fall back to generated tone

    def play(self, feedback_type: FeedbackType) -> None:
        """Play feedback sound for the given event type."""
        if not self._enabled:
            return

        # Try cached sound file first
        if feedback_type in self._sound_cache:
            audio_data, sample_rate = self._sound_cache[feedback_type]
            self._playback.play_async(audio_data, sample_rate)
            return

        # Fall back to generated tone
        frequency = TONE_FREQUENCIES.get(feedback_type, 440)
        duration = TONE_DURATIONS.get(feedback_type, 100)
        audio_data = generate_tone(frequency, duration)
        self._playback.play_async(audio_data, 22050)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable feedback sounds."""
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        """Return True if feedback sounds are enabled."""
        return self._enabled


class MockFeedback:
    """Mock feedback for testing.

    Records all feedback events without playing sounds.
    """

    def __init__(self) -> None:
        """Initialize mock feedback."""
        self._enabled = True
        self._events: list[FeedbackType] = []

    def play(self, feedback_type: FeedbackType) -> None:
        """Record feedback event."""
        if self._enabled:
            self._events.append(feedback_type)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable feedback."""
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        """Return True if enabled."""
        return self._enabled

    @property
    def events(self) -> list[FeedbackType]:
        """Get list of recorded events."""
        return self._events.copy()

    def clear(self) -> None:
        """Clear recorded events."""
        self._events.clear()


__all__ = [
    "MockFeedback",
    "SoundFeedback",
    "generate_tone",
    "load_wav_file",
]
