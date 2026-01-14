"""Voice loop orchestrator.

Coordinates the full voice interaction pipeline:
Wake Word → STT → Intent → LLM/Command → TTS → Playback
"""

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..audio.capture import AudioCapture
    from ..audio.playback import AudioPlayback
    from ..config import AraConfig
    from ..feedback import AudioFeedback
    from ..llm.model import LanguageModel
    from ..logger.interaction import InteractionLogger
    from ..stt.transcriber import Transcriber
    from ..tts.synthesizer import Synthesizer
    from ..wake_word.detector import WakeWordDetector
    from .mode import ModeManager

from datetime import UTC, datetime

from ..commands.reminder import (
    ReminderManager,
    ReminderStatus,
    format_time_local,
    parse_reminder_time,
)
from ..commands.system import SystemCommandHandler
from ..commands.timer import TimerManager, parse_duration
from ..config.loader import get_reminders_path
from ..config.personality import get_default_personality
from ..feedback import FeedbackType
from .intent import Intent, IntentClassifier, IntentType

logger = logging.getLogger(__name__)


def _get_ordinal(n: int) -> str:
    """Get ordinal representation of a number.

    Args:
        n: Number to convert (1-based).

    Returns:
        Ordinal string (first, second, ... tenth, 11th, 12th, etc.)
    """
    ordinals = {
        1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
        6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    }

    if n in ordinals:
        return ordinals[n]

    # For numbers > 10, use numeric ordinals
    if n % 10 == 1 and n % 100 != 11:
        return f"{n}st"
    elif n % 10 == 2 and n % 100 != 12:
        return f"{n}nd"
    elif n % 10 == 3 and n % 100 != 13:
        return f"{n}rd"
    else:
        return f"{n}th"


@dataclass
class InteractionResult:
    """Result of a voice interaction.

    Attributes:
        transcript: User's spoken text
        response_text: Assistant's response
        intent: Classified intent type
        latency_breakdown: Per-component latencies in ms
        total_latency_ms: Total end-to-end latency
        error: Error message if interaction failed
    """

    transcript: str
    response_text: str
    intent: str = "general_question"
    latency_breakdown: dict[str, int] = field(default_factory=dict)
    total_latency_ms: int = 0
    error: str | None = None


class Orchestrator:
    """Main voice loop orchestrator.

    Coordinates the complete voice interaction pipeline:
    1. Listen for wake word
    2. Capture user speech
    3. Transcribe to text (STT)
    4. Generate response (LLM)
    5. Synthesize speech (TTS)
    6. Play response audio
    """

    def __init__(
        self,
        audio_capture: "AudioCapture | None" = None,
        audio_playback: "AudioPlayback | None" = None,
        wake_word_detector: "WakeWordDetector | None" = None,
        transcriber: "Transcriber | None" = None,
        language_model: "LanguageModel | None" = None,
        synthesizer: "Synthesizer | None" = None,
        feedback: "AudioFeedback | None" = None,
        interaction_logger: "InteractionLogger | None" = None,
        device_id: str = "default",
        mode_manager: "ModeManager | None" = None,
        # Simplified init for testing - just llm and feedback
        llm: "LanguageModel | None" = None,
    ) -> None:
        """Initialize orchestrator with components.

        Args:
            audio_capture: Audio input capture
            audio_playback: Audio output playback
            wake_word_detector: Wake word detection
            transcriber: Speech-to-text
            language_model: LLM for response generation (or use 'llm' for short)
            synthesizer: Text-to-speech
            feedback: Audio feedback sounds
            interaction_logger: Optional logger for interactions
            device_id: Device identifier for logging
            mode_manager: Optional mode manager for system commands
            llm: Alias for language_model (for convenience)
        """
        self._capture = audio_capture
        self._playback = audio_playback
        self._wake_word = wake_word_detector
        self._transcriber = transcriber
        self._llm = language_model or llm
        self._synthesizer = synthesizer
        self._feedback = feedback
        self._interaction_logger = interaction_logger
        self._device_id = device_id
        self._mode_manager = mode_manager

        self._running = False
        self._thread: threading.Thread | None = None
        self._ready = False

        # Intent classification and command handling
        self._intent_classifier = IntentClassifier()
        self._timer_manager = TimerManager(on_expire=self._on_timer_expire)
        self._reminder_manager = ReminderManager(
            on_trigger=self._on_reminder_trigger,
            persistence_path=get_reminders_path(),
        )

        # System command handler (if mode manager is provided)
        self._system_handler = (
            SystemCommandHandler(mode_manager) if mode_manager else None
        )

        # Background check thread for timers/reminders
        self._check_thread: threading.Thread | None = None

        # Configuration
        self._silence_timeout_ms = 2000  # Stop recording after 2s silence
        self._max_recording_ms = 10000  # Max 10s recording

        # Load personality configuration
        self._personality = get_default_personality()
        if self._llm:
            self._llm.set_system_prompt(self._personality.system_prompt)
            logger.info(f"Loaded personality: {self._personality.name}")

        # Track missed reminders to deliver on first interaction
        self._missed_reminders: list = []
        self._check_missed_reminders()

    @classmethod
    def from_config(
        cls,
        config: "AraConfig",
        use_mocks: bool = False,
    ) -> "Orchestrator":
        """Create orchestrator from configuration.

        Args:
            config: Ara configuration
            use_mocks: Use mock implementations for testing

        Returns:
            Configured Orchestrator instance
        """
        from ..audio import create_audio_capture, create_audio_playback
        from ..feedback.audio import MockFeedback, SoundFeedback
        from ..llm import create_language_model
        from ..stt import create_transcriber
        from ..tts import create_synthesizer
        from ..wake_word import create_wake_word_detector

        # Create components
        audio_capture = create_audio_capture(config.audio, use_mock=use_mocks)
        audio_playback = create_audio_playback(config.audio, use_mock=use_mocks)
        wake_word = create_wake_word_detector(config.wake_word, use_mock=use_mocks)
        transcriber = create_transcriber(config.stt, use_mock=use_mocks)
        llm = create_language_model(config.llm, use_mock=use_mocks)
        synthesizer = create_synthesizer(config.tts, use_mock=use_mocks)

        if use_mocks:
            feedback: AudioFeedback = MockFeedback()
        else:
            feedback = SoundFeedback(audio_playback, config.feedback)

        # Initialize wake word detector - fall back to mock if initialization fails
        try:
            wake_word.initialize(
                keywords=[config.wake_word.keyword],
                sensitivity=config.wake_word.sensitivity,
            )
        except RuntimeError as e:
            # Fall back to mock if Porcupine not configured (e.g., no API key)
            logger.warning(f"Wake word initialization failed: {e}")
            logger.warning("Falling back to mock wake word detector")
            from ..wake_word import MockWakeWordDetector

            wake_word = MockWakeWordDetector()
            wake_word.initialize(
                keywords=[config.wake_word.keyword],
                sensitivity=config.wake_word.sensitivity,
            )

        orch = cls(
            audio_capture=audio_capture,
            audio_playback=audio_playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )

        orch._ready = True
        return orch

    def process_single_interaction(self) -> InteractionResult | None:
        """Process a single voice interaction.

        Waits for wake word, records speech, classifies intent, and generates response.

        Returns:
            InteractionResult or None if interaction failed
        """
        latencies: dict[str, int] = {}
        start_time = time.time()
        interaction_id = uuid.uuid4()

        try:
            # Step 1: Wait for wake word
            logger.debug("Listening for wake word...")
            wake_result = self._wait_for_wake_word()

            if not wake_result:
                return None

            latencies["wake_ms"] = int((time.time() - start_time) * 1000)

            # Play wake feedback
            self._feedback.play(FeedbackType.WAKE_WORD_DETECTED)
            logger.info("Wake word detected, listening for speech...")

            # Step 2: Record user speech
            stt_start = time.time()
            audio_data = self._record_speech()

            if not audio_data:
                logger.warning("No speech detected")
                return None

            # Step 3: Transcribe speech
            transcript_result = self._transcriber.transcribe(audio_data, 16000)
            transcript = transcript_result.text.strip()

            if not transcript:
                logger.warning("Empty transcription")
                return None

            latencies["stt_ms"] = int((time.time() - stt_start) * 1000)
            logger.info(f"Transcribed: '{transcript}'")

            # Step 4: Classify intent
            intent = self._intent_classifier.classify(transcript)
            logger.info(f"Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")

            # Step 5: Handle intent (command or LLM)
            response_start = time.time()
            response_text = self._handle_intent(intent, interaction_id)
            latencies["llm_ms"] = int((time.time() - response_start) * 1000)
            logger.info(f"Response: '{response_text[:50]}...'")

            # Step 6: Synthesize speech
            tts_start = time.time()
            synthesis_result = self._synthesizer.synthesize(response_text)
            latencies["tts_ms"] = int((time.time() - tts_start) * 1000)

            # Step 7: Play response
            play_start = time.time()
            self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            latencies["play_ms"] = int((time.time() - play_start) * 1000)

            total_latency = int((time.time() - start_time) * 1000)

            logger.info(
                f"Interaction complete: {total_latency}ms total "
                f"(STT:{latencies['stt_ms']}ms, LLM:{latencies['llm_ms']}ms, "
                f"TTS:{latencies['tts_ms']}ms)"
            )

            # Log the interaction
            if self._interaction_logger:
                latencies["total"] = total_latency
                self._interaction_logger.log(
                    transcript=transcript,
                    response=response_text,
                    intent=intent.type.value,
                    latency_ms=latencies,
                    entities=intent.entities,
                )

            return InteractionResult(
                transcript=transcript,
                response_text=response_text,
                intent=intent.type.value,
                latency_breakdown=latencies,
                total_latency_ms=total_latency,
            )

        except Exception as e:
            logger.error(f"Interaction failed: {e}")
            self._feedback.play(FeedbackType.ERROR)
            return InteractionResult(
                transcript="",
                response_text="",
                error=str(e),
            )

    def process(self, text: str) -> str:
        """Process text input directly (useful for testing).

        Args:
            text: User text input

        Returns:
            Response text
        """
        interaction_id = uuid.uuid4()
        intent = self._intent_classifier.classify(text)
        return self._handle_intent(intent, interaction_id)

    def _handle_intent(self, intent: Intent, interaction_id: uuid.UUID) -> str:
        """Handle classified intent and generate response.

        Args:
            intent: Classified intent
            interaction_id: ID of the current interaction

        Returns:
            Response text
        """
        if intent.type == IntentType.TIMER_SET:
            return self._handle_timer_set(intent, interaction_id)
        elif intent.type == IntentType.TIMER_CANCEL:
            return self._handle_timer_cancel(intent)
        elif intent.type == IntentType.TIMER_QUERY:
            return self._handle_timer_query()
        elif intent.type == IntentType.REMINDER_SET:
            return self._handle_reminder_set(intent, interaction_id)
        elif intent.type == IntentType.REMINDER_CANCEL:
            return self._handle_reminder_cancel(intent)
        elif intent.type == IntentType.REMINDER_QUERY:
            return self._handle_reminder_query()
        elif intent.type == IntentType.REMINDER_CLEAR_ALL:
            return self._handle_reminder_clear_all()
        elif intent.type == IntentType.HISTORY_QUERY:
            return self._handle_history_query(intent)
        elif intent.type == IntentType.WEB_SEARCH:
            return self._handle_web_search(intent)
        elif intent.type == IntentType.SYSTEM_COMMAND:
            return self._handle_system_command(intent)
        else:
            # Default to LLM for general questions
            llm_response = self._llm.generate(intent.raw_text)
            return llm_response.text.strip()

    def _handle_timer_set(self, intent: Intent, interaction_id: uuid.UUID) -> str:
        """Handle timer set intent."""
        duration_str = intent.entities.get("duration", "")
        name = intent.entities.get("name")

        duration_seconds = parse_duration(duration_str)
        if duration_seconds is None:
            # Try to extract from raw text
            duration_seconds = parse_duration(intent.raw_text)

        if duration_seconds is None or duration_seconds <= 0:
            return "I couldn't understand the timer duration. Please try again."

        timer = self._timer_manager.create(
            duration_seconds=duration_seconds,
            name=name,
            interaction_id=interaction_id,
        )

        formatted_time = self._timer_manager.format_remaining(timer)
        if name:
            return f"Timer '{name}' set for {formatted_time}."
        else:
            return f"Timer set for {formatted_time}."

    def _handle_timer_cancel(self, intent: Intent) -> str:
        """Handle timer cancel intent."""
        name = intent.entities.get("name")

        if name:
            timer = self._timer_manager.get_by_name(name)
            if timer:
                self._timer_manager.cancel(timer.id)
                return f"Timer '{name}' cancelled."
            else:
                return f"I couldn't find a timer called '{name}'."
        else:
            # Cancel the most recent active timer
            active = self._timer_manager.list_active()
            if active:
                timer = active[-1]
                self._timer_manager.cancel(timer.id)
                if timer.name:
                    return f"Timer '{timer.name}' cancelled."
                return "Timer cancelled."
            return "No active timers to cancel."

    def _handle_timer_query(self) -> str:
        """Handle timer query intent."""
        active = self._timer_manager.list_active()

        if not active:
            return "You have no active timers."

        if len(active) == 1:
            timer = active[0]
            remaining = self._timer_manager.format_remaining(timer)
            if timer.name:
                return f"Timer '{timer.name}' has {remaining} remaining."
            return f"Your timer has {remaining} remaining."

        lines = ["You have the following timers:"]
        for timer in active:
            remaining = self._timer_manager.format_remaining(timer)
            if timer.name:
                lines.append(f"  {timer.name}: {remaining}")
            else:
                lines.append(f"  Timer: {remaining}")

        return " ".join(lines)

    def _handle_reminder_set(self, intent: Intent, interaction_id: uuid.UUID) -> str:
        """Handle reminder set intent with time-aware confirmation."""
        message = intent.entities.get("message", intent.raw_text)
        time_str = intent.entities.get("time", "")

        remind_at = parse_reminder_time(time_str) if time_str else None

        if remind_at is None:
            # Try to parse from raw text
            remind_at = parse_reminder_time(intent.raw_text)

        if remind_at is None:
            return "When would you like me to remind you? Just say something like 'in 5 minutes' or 'at 3 PM'."

        # Validate duration is positive
        now = datetime.now(UTC)
        if remind_at <= now:
            return "Hmm, I can't set a reminder for the past! How about a few minutes from now?"

        self._reminder_manager.create(
            message=message,
            remind_at=remind_at,
            interaction_id=interaction_id,
        )

        # Format with both current time and target time
        current_time = format_time_local(now)
        target_time = format_time_local(remind_at)
        return f"Got it! It's {current_time} now, and I'll remind you at {target_time} to {message}."

    def _handle_reminder_cancel(self, intent: Intent) -> str:
        """Handle reminder cancel intent with support for cancel by number."""
        pending = self._reminder_manager.list_pending()

        if not pending:
            return "You don't have any reminders to cancel."

        # Check if user specified a number
        numbers = self._extract_reminder_numbers(intent.raw_text)

        if numbers:
            # Cancel by number(s)
            cancelled = []
            invalid = []

            for num in numbers:
                if 1 <= num <= len(pending):
                    reminder = pending[num - 1]
                    self._reminder_manager.cancel(reminder.id)
                    time_str = format_time_local(reminder.remind_at)
                    cancelled.append(f"the {_get_ordinal(num)} one ({reminder.message} at {time_str})")
                else:
                    invalid.append(num)

            if invalid:
                return f"Hmm, I only have {len(pending)} reminders right now. Want me to list them so you can pick the right one?"

            if len(cancelled) == 1:
                return f"Done! I've cancelled {cancelled[0]}."
            else:
                return f"Done! I've cancelled {len(cancelled)} reminders: {' and '.join(cancelled)}."

        # Check if user specified a description
        description = intent.entities.get("description", "")
        if description:
            for reminder in pending:
                if description.lower() in reminder.message.lower():
                    self._reminder_manager.cancel(reminder.id)
                    return f"Done! I've cancelled your reminder about {reminder.message}."
            return "I couldn't find a reminder about that. Want me to list what you have?"

        # Ambiguous - multiple reminders exist
        if len(pending) > 1:
            return "You have a few reminders - which one should I cancel? You can say the reminder number, like 'cancel reminder 2', or describe it."

        # Single reminder - cancel it
        reminder = pending[0]
        self._reminder_manager.cancel(reminder.id)
        return f"Done! I've cancelled your reminder to {reminder.message}."

    def _extract_reminder_numbers(self, text: str) -> list[int]:
        """Extract reminder numbers from text.

        Supports:
        - Cardinal numbers: "1", "2", "3"
        - Ordinal words: "first", "second", "third"
        - Multiple: "2, 4, and 5", "the third and sixth"

        Returns:
            List of 1-based reminder indices.
        """
        import re

        text_lower = text.lower()
        numbers = []

        # Ordinal word to number mapping
        ordinal_words = {
            "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
        }

        # Extract ordinal words
        for word, num in ordinal_words.items():
            if word in text_lower:
                numbers.append(num)

        # Extract cardinal numbers (including "reminder number N" and "reminder N")
        cardinal_matches = re.findall(r"(?:reminder\s+(?:number\s+)?)?(\d+)", text_lower)
        for match in cardinal_matches:
            num = int(match)
            if num not in numbers and num > 0:
                numbers.append(num)

        return sorted(set(numbers))

    def _handle_reminder_query(self) -> str:
        """Handle reminder query intent with numbered format."""
        pending = self._reminder_manager.list_pending()

        if not pending:
            return "Your schedule is clear - no reminders set right now!"

        if len(pending) == 1:
            reminder = pending[0]
            time_str = format_time_local(reminder.remind_at)
            return f"You have one reminder at {time_str} to {reminder.message}."

        # Multiple reminders - use numbered format
        parts = [f"You've got {len(pending)} reminders coming up!"]

        for i, reminder in enumerate(pending, 1):
            time_str = format_time_local(reminder.remind_at)
            ordinal = _get_ordinal(i)
            parts.append(f"{ordinal.capitalize()}, you have a reminder at {time_str} to {reminder.message}.")

        return " ".join(parts)

    def _handle_reminder_clear_all(self) -> str:
        """Handle clear all reminders intent."""
        count = self._reminder_manager.clear_all()

        if count == 0:
            return "You don't have any reminders to clear - your schedule is already empty!"

        return f"Done! I've cleared all {count} of your reminders. Fresh start!"

    def _check_missed_reminders(self) -> None:
        """Check for reminders that were missed during system downtime.

        Stores missed reminders to deliver on next interaction.
        """
        missed = self._reminder_manager.check_missed()
        if missed:
            self._missed_reminders = missed
            logger.info(f"Found {len(missed)} missed reminders to deliver")

    def _deliver_missed_reminders(self) -> str | None:
        """Deliver any missed reminders and return announcement.

        Returns:
            Missed reminder announcement text, or None if no missed reminders.
        """
        if not self._missed_reminders:
            return None

        messages = []
        for reminder in self._missed_reminders:
            # Mark as triggered
            reminder.status = ReminderStatus.TRIGGERED
            reminder.triggered_at = datetime.now(UTC)
            messages.append(
                f"Oops! I meant to remind you earlier but I was rebooting. "
                f"You wanted me to remind you to {reminder.message}."
            )

        # Save the state change
        self._reminder_manager._save()

        # Clear the list
        self._missed_reminders = []

        return " ".join(messages)

    def _handle_history_query(self, intent: Intent) -> str:
        """Handle history query intent."""
        if not self._interaction_logger:
            return "I don't have access to conversation history right now."

        from datetime import date, datetime, timedelta

        time_ref = intent.entities.get("time_ref", "recent")

        # Determine the date range
        today = date.today()
        if time_ref == "yesterday":
            target_date = today - timedelta(days=1)
            start = datetime.combine(target_date, datetime.min.time()).replace(
                tzinfo=UTC
            )
            end = datetime.combine(target_date, datetime.max.time()).replace(
                tzinfo=UTC
            )
        elif time_ref == "today":
            start = datetime.combine(today, datetime.min.time()).replace(
                tzinfo=UTC
            )
            end = datetime.now(UTC)
        else:
            # Recent - last 10 interactions
            interactions = self._interaction_logger.storage.get_recent(limit=10)
            if not interactions:
                return "I don't have any recent conversation history."

            lines = ["Here are your recent questions:"]
            for i, interaction in enumerate(interactions[:5], 1):
                lines.append(f"  {i}. {interaction.transcript}")

            return " ".join(lines)

        # Query by date range
        interactions = self._interaction_logger.storage.sqlite.get_by_date_range(
            start, end
        )

        if not interactions:
            if time_ref == "yesterday":
                return "You didn't ask me anything yesterday."
            else:
                return "I don't have any interactions recorded for today."

        lines = [f"Here's what you asked me {time_ref}:"]
        for i, interaction in enumerate(interactions[:5], 1):
            lines.append(f"  {i}. {interaction.transcript}")

        return " ".join(lines)

    def _handle_web_search(self, intent: Intent) -> str:
        """Handle web search intent.

        Performs a web search and summarizes results using the LLM.

        Args:
            intent: Classified web search intent.

        Returns:
            Response text with search summary.
        """
        try:
            from ..llm.search import SearchSummarizer, WebSearcher

            query = intent.entities.get("query", intent.raw_text)

            # Try to perform web search
            searcher = WebSearcher(max_results=5)
            results = searcher.search(query)

            if not results:
                # Fall back to local LLM if search fails
                logger.warning("Web search returned no results, falling back to local LLM")
                llm_response = self._llm.generate(intent.raw_text)
                return llm_response.text.strip()

            # Summarize results using LLM
            summarizer = SearchSummarizer(llm=self._llm)
            summary = summarizer.summarize(query, results)

            return summary

        except ImportError:
            # duckduckgo_search not installed
            logger.warning("Web search not available, falling back to local LLM")
            llm_response = self._llm.generate(intent.raw_text)
            return llm_response.text.strip()

        except Exception as e:
            # Any other error, graceful degradation to local LLM
            logger.error(f"Web search failed: {e}, falling back to local LLM")
            llm_response = self._llm.generate(intent.raw_text)
            return llm_response.text.strip()

    def _handle_system_command(self, intent: Intent) -> str:
        """Handle system command intent.

        Args:
            intent: Classified system command intent.

        Returns:
            Response text.
        """
        command = intent.entities.get("command", "")

        if not self._system_handler:
            return "System commands are not available in this mode."

        # Play mode change feedback for mode-changing commands
        if command in ("offline", "online") and self._feedback:
            self._feedback.play(FeedbackType.MODE_CHANGE)

        return self._system_handler.handle(command)

    def _on_timer_expire(self, timer: "TimerManager") -> None:
        """Callback when a timer expires."""
        logger.info(f"Timer expired: {timer.name or 'unnamed'}")
        self._feedback.play(FeedbackType.TIMER_ALERT)

        # Optionally announce the timer
        if timer.name:
            message = f"Your timer '{timer.name}' has finished."
        else:
            message = "Your timer has finished."

        try:
            synthesis_result = self._synthesizer.synthesize(message)
            self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
        except Exception as e:
            logger.error(f"Failed to announce timer: {e}")

    def _on_reminder_trigger(self, reminder: "ReminderManager") -> None:
        """Callback when a reminder triggers."""
        logger.info(f"Reminder triggered: {reminder.message}")
        self._feedback.play(FeedbackType.REMINDER_ALERT)

        # Announce the reminder
        message = f"Reminder: {reminder.message}"

        try:
            synthesis_result = self._synthesizer.synthesize(message)
            self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
        except Exception as e:
            logger.error(f"Failed to announce reminder: {e}")

    def _wait_for_wake_word(self) -> bool:
        """Wait for wake word detection.

        Returns:
            True if wake word detected
        """
        self._capture.start()

        try:
            for chunk in self._capture.stream():
                result = self._wake_word.process(chunk)
                if result.detected:
                    return True

                # Check if we should stop
                if not self._running:
                    return False

        finally:
            self._capture.stop()

        return False

    def _record_speech(self) -> bytes:
        """Record user speech until silence detected.

        Returns:
            Recorded audio bytes
        """
        audio_buffer = b""
        silence_start: float | None = None
        recording_start = time.time()

        # Small delay to avoid PyAudio segfault from rapid stop/start
        time.sleep(0.1)
        self._capture.start()

        try:
            for chunk in self._capture.stream():
                audio_buffer += chunk.data

                # Check for silence (simple energy-based detection)
                energy = self._calculate_energy(chunk.data)
                is_silence = energy < 500  # Threshold

                if is_silence:
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) * 1000 > self._silence_timeout_ms:
                        # Silence timeout reached
                        logger.debug("Silence detected, stopping recording")
                        break
                else:
                    silence_start = None

                # Check max recording time
                if (time.time() - recording_start) * 1000 > self._max_recording_ms:
                    logger.debug("Max recording time reached")
                    break

        finally:
            self._capture.stop()

        return audio_buffer

    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calculate audio energy for silence detection."""
        import struct

        if len(audio_data) < 2:
            return 0.0

        # Convert to int16 samples
        num_samples = len(audio_data) // 2
        samples = struct.unpack(f"{num_samples}h", audio_data)

        # Calculate RMS energy
        sum_squares = sum(s * s for s in samples)
        rms = (sum_squares / num_samples) ** 0.5

        return rms

    def start(self) -> None:
        """Start the voice loop in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Start timer/reminder check thread
        self._check_thread = threading.Thread(
            target=self._check_timers_and_reminders, daemon=True
        )
        self._check_thread.start()

        logger.info("Voice loop started")

    def stop(self) -> None:
        """Stop the voice loop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._check_thread is not None:
            self._check_thread.join(timeout=2.0)
            self._check_thread = None
        logger.info("Voice loop stopped")

    def _run_loop(self) -> None:
        """Main voice loop."""
        while self._running:
            try:
                result = self.process_single_interaction()
                if result and result.error:
                    logger.error(f"Interaction error: {result.error}")
            except Exception as e:
                logger.error(f"Voice loop error: {e}")
                time.sleep(1)  # Brief pause before retry

    @property
    def is_ready(self) -> bool:
        """Check if orchestrator is ready."""
        return self._ready

    @property
    def is_running(self) -> bool:
        """Check if voice loop is running."""
        return self._running

    @property
    def timer_manager(self) -> TimerManager:
        """Get the timer manager."""
        return self._timer_manager

    @property
    def reminder_manager(self) -> ReminderManager:
        """Get the reminder manager."""
        return self._reminder_manager

    def _check_timers_and_reminders(self) -> None:
        """Background thread to check for expired timers and due reminders."""
        while self._running:
            try:
                # Check for expired timers
                self._timer_manager.check_expired()

                # Check for due reminders
                self._reminder_manager.check_due()

            except Exception as e:
                logger.error(f"Error checking timers/reminders: {e}")

            # Check every second
            time.sleep(1)


__all__ = ["InteractionResult", "Orchestrator"]
