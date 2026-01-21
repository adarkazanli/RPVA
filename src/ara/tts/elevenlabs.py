"""ElevenLabs TTS synthesizer with emotion support.

Provides high-quality, emotionally expressive speech synthesis using the ElevenLabs API.
"""

import logging
import os
import time
from enum import Enum, auto

from .synthesizer import SynthesisResult

logger = logging.getLogger(__name__)

# Check for elevenlabs availability
ELEVENLABS_AVAILABLE = False
VoiceSettings = None
try:
    from elevenlabs import ElevenLabs
    from elevenlabs.types import VoiceSettings

    ELEVENLABS_AVAILABLE = True
except ImportError:
    pass


class Emotion(Enum):
    """Supported emotional tones for TTS."""

    NEUTRAL = auto()
    WARM = auto()  # Friendly, welcoming
    CHEERFUL = auto()  # Happy, excited
    CALM = auto()  # Soothing, reassuring
    CONCERNED = auto()  # Empathetic, caring
    ENTHUSIASTIC = auto()  # Energetic, excited
    PROFESSIONAL = auto()  # Clear, informative


# Emotion to next_text mapping for ElevenLabs
EMOTION_CUES = {
    Emotion.NEUTRAL: "",
    Emotion.WARM: "she said warmly",
    Emotion.CHEERFUL: "she said cheerfully",
    Emotion.CALM: "she said calmly and soothingly",
    Emotion.CONCERNED: "she said with concern",
    Emotion.ENTHUSIASTIC: "she said enthusiastically",
    Emotion.PROFESSIONAL: "she said clearly and professionally",
}


class ElevenLabsSynthesizer:
    """Text-to-speech synthesizer using ElevenLabs API.

    Provides emotionally expressive speech synthesis with automatic
    emotion detection based on response context.
    """

    # Default voice - Bella (soft, gentle female voice)
    DEFAULT_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Bella
    DEFAULT_MODEL = "eleven_multilingual_v2"
    TARGET_SAMPLE_RATE = 22050

    # Alternative voices
    VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # Warm, natural
        "domi": "AZnzlk1XvdvUeBnXmlld",  # Strong, confident
        "bella": "EXAVITQu4vr4xnSDxMaL",  # Soft, gentle
        "josh": "TxGEqnHWrfWFTfGW9XjX",  # Deep, professional
        "adam": "pNInz6obpgDQGcFmaJgB",  # Clear, neutral
    }

    def __init__(
        self,
        api_key: str | None = None,
        voice_id: str | None = None,
        model: str | None = None,
        default_emotion: Emotion = Emotion.WARM,
    ) -> None:
        """Initialize ElevenLabs synthesizer.

        Args:
            api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
            voice_id: Voice ID to use (defaults to Rachel)
            model: Model ID (defaults to eleven_multilingual_v2)
            default_emotion: Default emotion when not detected
        """
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self._voice_id = voice_id or self.DEFAULT_VOICE_ID
        self._model = model or self.DEFAULT_MODEL
        self._default_emotion = default_emotion
        self._speed = 1.0
        self._client: ElevenLabs | None = None

        # Initialize client if API key available
        if self._api_key and ELEVENLABS_AVAILABLE:
            try:
                self._client = ElevenLabs(api_key=self._api_key)
                logger.info("ElevenLabs client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize ElevenLabs client: {e}")
                self._client = None

    @property
    def is_available(self) -> bool:
        """Check if ElevenLabs is available and configured."""
        return (
            ELEVENLABS_AVAILABLE
            and self._client is not None
            and self._api_key is not None
            and self._api_key != "your-elevenlabs-api-key"
        )

    def synthesize(
        self,
        text: str,
        emotion: Emotion | None = None,
    ) -> SynthesisResult:
        """Convert text to speech with emotional tone.

        Args:
            text: Text to synthesize
            emotion: Emotional tone (auto-detected if not provided)

        Returns:
            SynthesisResult with PCM audio data

        Raises:
            RuntimeError: If synthesis fails
        """
        start_time = time.time()

        if not self.is_available:
            raise RuntimeError("ElevenLabs TTS not available")

        # Auto-detect emotion if not provided
        if emotion is None:
            emotion = self._detect_emotion(text)

        # Get emotion cue for next_text
        emotion_cue = EMOTION_CUES.get(emotion, "")

        try:
            # Voice settings for natural, expressive speech
            # - stability: Lower = more expressive variation (0.3-0.5 ideal)
            # - similarity_boost: How closely to match original voice
            # - style: Exaggeration of style (adds expressiveness)
            # - use_speaker_boost: Enhances voice clarity
            voice_settings = VoiceSettings(
                stability=0.4,  # Lower for more natural variation
                similarity_boost=0.75,
                style=0.3,  # Add some style/expressiveness
                use_speaker_boost=True,
            )

            # Generate audio using ElevenLabs API
            audio_generator = self._client.text_to_speech.convert(
                text=text,
                voice_id=self._voice_id,
                model_id=self._model,
                output_format="pcm_22050",  # 22050 Hz 16-bit PCM
                next_text=emotion_cue if emotion_cue else None,
                voice_settings=voice_settings,
            )

            # Collect audio bytes from generator
            audio_data = b"".join(audio_generator)

            # Calculate duration (16-bit = 2 bytes per sample)
            duration_ms = int(len(audio_data) / (self.TARGET_SAMPLE_RATE * 2) * 1000)
            latency_ms = int((time.time() - start_time) * 1000)

            logger.debug(
                f"ElevenLabs synthesized '{text[:30]}...' "
                f"(emotion={emotion.name}) in {latency_ms}ms ({duration_ms}ms audio)"
            )

            return SynthesisResult(
                audio=audio_data,
                sample_rate=self.TARGET_SAMPLE_RATE,
                duration_ms=max(1, duration_ms),
                latency_ms=latency_ms,
            )

        except Exception as e:
            raise RuntimeError(f"ElevenLabs synthesis failed: {e}") from e

    def _detect_emotion(self, text: str) -> Emotion:
        """Detect appropriate emotion from text content.

        Args:
            text: The text to analyze

        Returns:
            Detected emotion or default
        """
        text_lower = text.lower()

        # Greeting patterns -> warm
        if any(
            word in text_lower
            for word in ["hello", "hi ", "hey ", "good morning", "good evening", "welcome"]
        ):
            return Emotion.WARM

        # Excitement/positive patterns -> cheerful
        if any(
            word in text_lower
            for word in ["great", "awesome", "excellent", "wonderful", "exciting", "!"]
        ):
            return Emotion.CHEERFUL

        # Concern/empathy patterns -> concerned
        if any(
            word in text_lower
            for word in ["sorry", "unfortunately", "problem", "issue", "error", "failed"]
        ):
            return Emotion.CONCERNED

        # Calming patterns -> calm
        if any(
            word in text_lower
            for word in ["relax", "don't worry", "it's okay", "take your time", "no rush"]
        ):
            return Emotion.CALM

        # Weather/information patterns -> professional
        if any(
            word in text_lower
            for word in ["weather", "temperature", "forecast", "degrees", "currently"]
        ):
            return Emotion.PROFESSIONAL

        # Reminder/task patterns -> enthusiastic
        if any(word in text_lower for word in ["reminder", "remember", "don't forget", "set for"]):
            return Emotion.ENTHUSIASTIC

        return self._default_emotion

    def set_voice(self, voice_id: str) -> None:
        """Set the voice for synthesis.

        Args:
            voice_id: Voice ID or name (e.g., "rachel", "josh")
        """
        # Check if it's a named voice
        if voice_id.lower() in self.VOICES:
            self._voice_id = self.VOICES[voice_id.lower()]
        else:
            self._voice_id = voice_id

    def set_speed(self, speed: float) -> None:
        """Set speech speed (not directly supported by ElevenLabs API).

        Args:
            speed: Speed multiplier (stored but not used)
        """
        self._speed = max(0.5, min(2.0, speed))

    def set_emotion(self, emotion: Emotion) -> None:
        """Set the default emotion for synthesis.

        Args:
            emotion: Default emotional tone
        """
        self._default_emotion = emotion

    def get_available_voices(self) -> list[str]:
        """List available voice names.

        Returns:
            List of voice names
        """
        return list(self.VOICES.keys())


__all__ = ["ElevenLabsSynthesizer", "Emotion", "ELEVENLABS_AVAILABLE"]
