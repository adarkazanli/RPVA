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

from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..commands.reminder import (
    Reminder,
    ReminderManager,
    ReminderStatus,
    format_time_local,
    parse_reminder_time,
)
from ..commands.system import SystemCommandHandler
from ..commands.timer import Timer, TimerManager, TimerStatus, parse_duration
from ..config.loader import get_reminders_path
from ..config.personality import get_default_personality
from ..config.user_profile import load_user_profile
from ..feedback import FeedbackType
from ..search import create_search_client
from .intent import Intent, IntentClassifier, IntentType

logger = logging.getLogger(__name__)

# Interaction timing log file
_INTERACTION_LOG_DIR = Path("logs")
_INTERACTION_LOG_FILE = _INTERACTION_LOG_DIR / "interactions.txt"


def _log_interaction_timing(event: str, transcript: str = "") -> None:
    """Log interaction timing to text file.

    Args:
        event: Event type ('captured' or 'responded')
        transcript: Optional transcript text for context
    """
    try:
        _INTERACTION_LOG_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if transcript:
            line = f'{timestamp}: Voice agent {event} -> "{transcript}"\n'
        else:
            line = f"{timestamp}: Voice agent {event}\n"

        with open(_INTERACTION_LOG_FILE, "a") as f:
            f.write(line)
    except Exception as e:
        logger.debug(f"Failed to write interaction timing log: {e}")


def _get_ordinal(n: int) -> str:
    """Get ordinal representation of a number.

    Args:
        n: Number to convert (1-based).

    Returns:
        Ordinal string (first, second, ... tenth, 11th, 12th, etc.)
    """
    ordinals = {
        1: "first",
        2: "second",
        3: "third",
        4: "fourth",
        5: "fifth",
        6: "sixth",
        7: "seventh",
        8: "eighth",
        9: "ninth",
        10: "tenth",
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
        self._system_handler = SystemCommandHandler(mode_manager) if mode_manager else None

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

        # Countdown announcement tracking (protected by _countdown_lock)
        self._countdown_lock = threading.Lock()
        self._countdown_active: dict[uuid.UUID, bool] = {}
        self._countdown_in_progress = False
        self._countdown_interval = 1.0  # 1 second between numbers

        # Load user profile for personalized announcements
        self._user_profile = load_user_profile()
        self._user_name = self._user_profile.name
        if self._user_name:
            logger.info(f"Loaded user profile: {self._user_name}")

        # Initialize search client (with fallback to mock if API key not available)
        self._search_client = create_search_client()
        search_client_type = type(self._search_client).__name__
        logger.info(f"Search client initialized: {search_client_type}")

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

        # Ensure required components are available
        if (
            not self._feedback
            or not self._transcriber
            or not self._synthesizer
            or not self._playback
        ):
            logger.error("Missing required components for interaction")
            return None

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

            # Log capture timing
            _log_interaction_timing("captured", transcript)

            # Step 4: Classify intent
            intent = self._intent_classifier.classify(transcript)
            logger.info(f"Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")

            # Step 5: Handle intent (command or LLM)
            response_start = time.time()
            response_text = self._handle_intent(intent, interaction_id)
            latencies["llm_ms"] = int((time.time() - response_start) * 1000)
            logger.info(f"Response: '{response_text[:50]}...'")

            # Log response timing
            _log_interaction_timing("responded", response_text)

            # Step 6: Synthesize speech
            tts_start = time.time()
            synthesis_result = self._synthesizer.synthesize(response_text)
            latencies["tts_ms"] = int((time.time() - tts_start) * 1000)

            # Step 7: Play response
            play_start = time.time()
            self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            latencies["play_ms"] = int((time.time() - play_start) * 1000)

            # Step 8: Check for follow-up if response ended with a question
            if response_text.strip().endswith("?"):
                logger.info("Response ended with question, listening for follow-up...")
                follow_up_audio = self._record_follow_up(timeout_ms=5000)

                if follow_up_audio:
                    # Process the follow-up
                    follow_up_result = self._transcriber.transcribe(follow_up_audio, 16000)
                    follow_up_text = follow_up_result.text.strip()

                    if follow_up_text:
                        logger.info(f"Follow-up: '{follow_up_text}'")
                        _log_interaction_timing("captured", follow_up_text)

                        # Classify and handle follow-up
                        follow_up_intent = self._intent_classifier.classify(follow_up_text)
                        follow_up_response = self._handle_intent(follow_up_intent, interaction_id)
                        _log_interaction_timing("responded", follow_up_response)

                        # Synthesize and play follow-up response
                        follow_up_synthesis = self._synthesizer.synthesize(follow_up_response)
                        self._playback.play(
                            follow_up_synthesis.audio, follow_up_synthesis.sample_rate
                        )

                        # Update transcript/response for logging
                        transcript = f"{transcript} | {follow_up_text}"
                        response_text = f"{response_text} | {follow_up_response}"

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
        elif intent.type == IntentType.REMINDER_TIME_LEFT:
            return self._handle_reminder_time_left(intent)
        elif intent.type == IntentType.HISTORY_QUERY:
            return self._handle_history_query(intent)
        elif intent.type == IntentType.WEB_SEARCH:
            return self._handle_web_search(intent)
        elif intent.type == IntentType.SYSTEM_COMMAND:
            return self._handle_system_command(intent)
        elif intent.type == IntentType.USER_NAME_SET:
            return self._handle_user_name_set(intent)
        elif intent.type == IntentType.USER_PASSWORD_SET:
            return self._handle_user_password_set(intent)
        elif intent.type == IntentType.TIME_QUERY:
            return self._handle_time_query()
        elif intent.type == IntentType.DATE_QUERY:
            return self._handle_date_query()
        elif intent.type == IntentType.FUTURE_TIME_QUERY:
            return self._handle_future_time_query(intent)
        else:
            # Default to LLM for general questions
            if self._llm is None:
                return "I'm not able to process that request right now."

            # Inject current time context for the LLM
            now = datetime.now()
            time_str = now.strftime("%-I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            context = f"[Current time: {time_str}, {date_str}]"

            # Add user name context if available
            if self._user_name:
                context += f" [User's name: {self._user_name}]"

            # Combine context with user query
            query_with_context = f"{context}\n\nUser: {intent.raw_text}"

            llm_response = self._llm.generate(query_with_context)
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

        # Format concise response with target time
        target_time = format_time_local(remind_at)
        return f"Got it! Reminder set for {target_time}."

    def _handle_reminder_cancel(self, intent: Intent) -> str:
        """Handle reminder cancel intent with concise responses."""
        pending = self._reminder_manager.list_pending()

        if not pending:
            return "No reminders to cancel."

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
                    # Signal countdown to stop if running
                    self._countdown_active[reminder.id] = False
                    cancelled.append(reminder.message)
                else:
                    invalid.append(num)

            if invalid:
                return f"Only have {len(pending)} reminders. Which one?"

            if len(cancelled) == 1:
                return f"Done! Cancelled: {cancelled[0]}."
            else:
                return f"Done! Cancelled {len(cancelled)} reminders."

        # Check if user specified a description
        description = intent.entities.get("description", "")
        if description:
            for reminder in pending:
                if description.lower() in reminder.message.lower():
                    self._reminder_manager.cancel(reminder.id)
                    # Signal countdown to stop if running
                    self._countdown_active[reminder.id] = False
                    return f"Done! Cancelled: {reminder.message}."
            return "Couldn't find that reminder. Want me to list them?"

        # Ambiguous - multiple reminders exist
        if len(pending) > 1:
            return "Which reminder? Say the number or describe it."

        # Single reminder - cancel it
        reminder = pending[0]
        self._reminder_manager.cancel(reminder.id)
        # Signal countdown to stop if running
        self._countdown_active[reminder.id] = False
        return f"Done! Cancelled: {reminder.message}."

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
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "fifth": 5,
            "sixth": 6,
            "seventh": 7,
            "eighth": 8,
            "ninth": 9,
            "tenth": 10,
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
        """Handle reminder query intent with concise numbered format."""
        pending = self._reminder_manager.list_pending()

        if not pending:
            return "No reminders set."

        if len(pending) == 1:
            reminder = pending[0]
            time_str = format_time_local(reminder.remind_at)
            return f"One reminder at {time_str} to {reminder.message}."

        # Multiple reminders - use concise numbered format
        parts = [f"You have {len(pending)} reminders."]

        for i, reminder in enumerate(pending, 1):
            time_str = format_time_local(reminder.remind_at)
            ordinal = _get_ordinal(i)
            parts.append(f"{ordinal.capitalize()}, at {time_str} to {reminder.message}.")

        return " ".join(parts)

    def _handle_reminder_clear_all(self) -> str:
        """Handle clear all reminders intent with concise response."""
        count = self._reminder_manager.clear_all()

        if count == 0:
            return "No reminders to clear."

        return f"Done! Cleared {count} reminders."

    def _handle_reminder_time_left(self, intent: Intent) -> str:
        """Handle reminder time remaining query.

        Args:
            intent: Classified reminder time left intent.

        Returns:
            Response with time remaining until next reminder.
        """
        pending = self._reminder_manager.list_pending()

        if not pending:
            return "You have no active reminders."

        search_term = intent.entities.get("search", "")
        now = datetime.now(UTC)

        # If search term provided, find matching reminder
        if search_term:
            search_lower = search_term.lower()
            for reminder in pending:
                if search_lower in reminder.message.lower():
                    time_diff = reminder.remind_at - now
                    minutes = int(time_diff.total_seconds() / 60)
                    if minutes < 1:
                        return f"Your reminder to {reminder.message} is coming up any moment!"
                    elif minutes == 1:
                        return f"About 1 minute until your reminder to {reminder.message}."
                    elif minutes < 60:
                        return f"About {minutes} minutes until your reminder to {reminder.message}."
                    else:
                        hours = minutes // 60
                        mins = minutes % 60
                        if mins > 0:
                            return f"About {hours} hour{'s' if hours > 1 else ''} and {mins} minutes until your reminder to {reminder.message}."
                        return f"About {hours} hour{'s' if hours > 1 else ''} until your reminder to {reminder.message}."

        # No search term or no match - show next reminder
        next_reminder = pending[0]  # Already sorted by time
        time_diff = next_reminder.remind_at - now
        minutes = int(time_diff.total_seconds() / 60)
        time_str = format_time_local(next_reminder.remind_at)

        if minutes < 1:
            return f"Your next reminder is coming up any moment - to {next_reminder.message}!"
        elif minutes == 1:
            return (
                f"About 1 minute until your next reminder at {time_str} to {next_reminder.message}."
            )
        elif minutes < 60:
            return f"About {minutes} minutes until your next reminder at {time_str} to {next_reminder.message}."
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins > 0:
                return f"About {hours} hour{'s' if hours > 1 else ''} and {mins} minutes until your next reminder to {next_reminder.message}."
            return f"About {hours} hour{'s' if hours > 1 else ''} until your next reminder to {next_reminder.message}."

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
        # Read from the interaction log file directly
        log_file = _INTERACTION_LOG_FILE

        if not log_file.exists():
            return "I don't have any conversation history yet."

        try:
            with open(log_file) as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read interaction log: {e}")
            return "I couldn't access the conversation history."

        if not lines:
            return "I don't have any conversation history yet."

        query_type = intent.entities.get("query_type", "list")
        search_content = intent.entities.get("search_content", "")
        time_ref = intent.entities.get("time_ref", "recent")

        # Parse the log entries - each entry has timestamp (datetime) and content (str)
        entries: list[dict[str, datetime | str]] = []
        for line in lines:
            # Format: "2026-01-14 10:32:18: Voice agent captured -> "text""
            if "captured ->" in line:
                try:
                    # Extract timestamp and content
                    timestamp_str = (
                        line.split(":")[0] + ":" + line.split(":")[1] + ":" + line.split(":")[2]
                    )
                    timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S")
                    content = line.split('-> "')[1].rstrip('"\n')
                    entries.append({"timestamp": timestamp, "content": content})
                except (IndexError, ValueError):
                    continue

        if not entries:
            return "I don't have any conversation history yet."

        # Helper function for fuzzy word matching
        def fuzzy_match(search_text: str, content_text: str) -> bool:
            """Check if search terms match content using word-based fuzzy matching."""
            # Extract meaningful words (skip common words)
            skip_words = {
                "the",
                "a",
                "an",
                "in",
                "on",
                "at",
                "to",
                "for",
                "of",
                "and",
                "or",
                "is",
                "it",
                "that",
                "this",
                "about",
                "did",
                "i",
                "you",
                "my",
                "me",
                "ask",
                "asked",
                "say",
                "said",
                "mention",
                "mentioned",
                "when",
                "how",
            }
            search_words = [
                w for w in search_text.lower().split() if w not in skip_words and len(w) > 2
            ]
            content_lower = content_text.lower()

            if not search_words:
                return False

            # Check if most meaningful words are present
            matches = sum(1 for w in search_words if w in content_lower)
            return matches >= len(search_words) * 0.5  # At least 50% of words match

        # Handle different query types
        if query_type == "time_since" and search_content:
            # Search for content and calculate time since
            now = datetime.now()

            for entry in reversed(entries):  # Search from most recent
                entry_content = str(entry["content"])
                entry_timestamp = entry["timestamp"]
                if not isinstance(entry_timestamp, datetime):
                    continue
                if fuzzy_match(search_content, entry_content):
                    time_diff = now - entry_timestamp
                    minutes = int(time_diff.total_seconds() / 60)

                    if minutes < 1:
                        return "You said that just now!"
                    elif minutes == 1:
                        return "You said that about a minute ago."
                    elif minutes < 60:
                        return f"You said that about {minutes} minutes ago."
                    else:
                        hours = minutes // 60
                        if hours == 1:
                            return "You said that about an hour ago."
                        else:
                            return f"You said that about {hours} hours ago."

            return "I couldn't find when you mentioned that. Would you like me to list your recent history?"

        elif query_type == "content_check" and search_content:
            # Check if user mentioned something
            for entry in reversed(entries):
                entry_content = str(entry["content"])
                entry_timestamp = entry["timestamp"]
                if not isinstance(entry_timestamp, datetime):
                    continue
                if fuzzy_match(search_content, entry_content):
                    time_diff = datetime.now() - entry_timestamp
                    minutes = int(time_diff.total_seconds() / 60)
                    time_str = f"{minutes} minutes ago" if minutes > 1 else "just now"
                    return f"Yes! You mentioned that {time_str}."

            return "I don't see that in your recent history."

        else:
            # Default: list recent history
            from datetime import date as dt_date

            today = dt_date.today()

            # Filter entries with valid timestamps
            def get_entry_date(e: dict[str, datetime | str]) -> dt_date | None:
                ts = e.get("timestamp")
                if isinstance(ts, datetime):
                    return ts.date()
                return None

            if time_ref == "yesterday":
                yesterday = today - timedelta(days=1)
                filtered = [e for e in entries if get_entry_date(e) == yesterday]
                if not filtered:
                    return "You didn't ask me anything yesterday."
                prefix = "Here's what you asked me yesterday:"
            elif time_ref == "today":
                filtered = [e for e in entries if get_entry_date(e) == today]
                if not filtered:
                    return "You haven't asked me anything today yet."
                prefix = "Here's what you asked me today:"
            else:
                # Recent - last 5 interactions
                filtered = entries[-5:]
                prefix = "Here are your recent interactions:"

            result_lines = [prefix]
            for i, entry in enumerate(filtered[-5:], 1):
                content = str(entry.get("content", ""))
                if len(content) > 50:
                    content = content[:47] + "..."
                result_lines.append(f"  {i}. {content}")

            return " ".join(result_lines)

    def _handle_web_search(self, intent: Intent) -> str:
        """Handle web search intent.

        Performs a web search using Tavily and returns results.
        Prefixes responses with source attribution to distinguish
        from LLM-generated content.

        Args:
            intent: Classified web search intent.

        Returns:
            Response text with search results and source attribution.
        """
        # Use the full raw text as the search query to preserve context
        # The entities["query"] often only captures a part (like location)
        # but we want the full context like "latest news in Austin"
        query = intent.raw_text.strip()

        # Clean up the query - remove trailing punctuation for better search
        query = query.rstrip("?!.")

        search_client_type = type(self._search_client).__name__
        logger.info(f"Web search query: '{query}' (client: {search_client_type})")

        try:
            # Use Tavily for search
            result = self._search_client.search(query, max_results=3, include_answer=True)

            if not result.success:
                logger.warning(f"Search failed (client: {search_client_type}): {result.error}")
                if self._llm is None:
                    return "I couldn't search for that right now."
                # Fall back to LLM
                logger.info("Falling back to LLM for response")
                llm_response = self._llm.generate(intent.raw_text)
                return llm_response.text.strip()

            # Log what we got back
            logger.info(
                f"Search result: success={result.success}, "
                f"has_answer={bool(result.answer)}, "
                f"num_results={len(result.results)}"
            )

            # Build source attribution prefix
            today = datetime.now().strftime("%B %d, %Y")
            greeting = f"{self._user_name}, " if self._user_name else ""

            # Check if this is a news-related query
            query_lower = query.lower()
            is_news_query = any(
                word in query_lower
                for word in ["news", "latest", "recent", "happening", "headlines"]
            )

            # If we have a direct answer, use it
            if result.answer:
                # For voice, keep it concise
                answer = result.answer
                # Truncate if too long for voice
                if len(answer) > 250:
                    answer = answer[:247] + "..."

                # Build natural response - no awkward "according to web search" prefix
                # Just include greeting and date context for news queries
                if is_news_query:
                    prefix = f"{greeting}as of {today}, "
                elif greeting:
                    prefix = f"{greeting}"
                else:
                    prefix = ""

                logger.debug(f"Returning search answer: {answer[:50]}...")
                return f"{prefix}{answer}"

            # Otherwise, summarize the results with source info
            if result.results:
                summaries = []
                sources = []
                for r in result.results[:3]:
                    content = r.get("content", "")
                    title = r.get("title", "")
                    if content:
                        # Take first ~80 chars of each result
                        summaries.append(content[:80])
                    if title:
                        sources.append(title)

                if summaries:
                    combined = " ".join(summaries)
                    if len(combined) > 250:
                        combined = combined[:247] + "..."

                    # Build natural response - no awkward prefix
                    if is_news_query:
                        prefix = f"{greeting}as of {today}, "
                    elif greeting:
                        prefix = f"{greeting}"
                    else:
                        prefix = ""

                    return f"{prefix}{combined}"

            logger.warning("Search succeeded but no answer or results returned")
            return "I searched but couldn't find relevant information."

        except Exception as e:
            logger.error(f"Web search exception (client: {search_client_type}): {e}")
            if self._llm is None:
                return "I encountered an error while searching."
            # Fall back to LLM
            logger.info("Falling back to LLM due to exception")
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

    def _handle_user_name_set(self, intent: Intent) -> str:
        """Handle user name set intent.

        Args:
            intent: Classified user name set intent.

        Returns:
            Response text confirming the name change.
        """
        name = intent.entities.get("name", "")
        password = intent.entities.get("password", "")

        if not name:
            return "What should I call you?"

        # Check if profile is password protected
        if self._user_profile.is_password_protected:
            if not password:
                return "Your profile is password protected. Please say your password to change your name."

            if not self._user_profile.verify_password(password):
                return "That password doesn't match. Please try again with the correct password."

        # Update the profile
        self._user_profile.name = name
        self._user_name = name

        # Save to disk
        from ..config.user_profile import save_user_profile

        save_user_profile(self._user_profile)

        logger.info(f"User name set to: {name}")
        return f"Got it, {name}! I'll use your name from now on."

    def _handle_user_password_set(self, intent: Intent) -> str:
        """Handle user password set intent.

        Args:
            intent: Classified password set intent.

        Returns:
            Response text confirming password was set.
        """
        password = intent.entities.get("password", "")

        if not password:
            return "What password would you like to use?"

        # Set the password
        self._user_profile.set_password(password)

        # Save to disk
        from ..config.user_profile import save_user_profile

        save_user_profile(self._user_profile)

        logger.info("User password set")
        return "Password set! I'll require it before changing your name."

    def _handle_time_query(self) -> str:
        """Handle time query intent by returning the actual system time.

        Returns:
            Response text with current time.
        """
        now = datetime.now()
        # Format: "It's 3:45 PM"
        time_str = now.strftime("%-I:%M %p")
        # Add warmth with user name if available
        if self._user_name:
            return f"It's {time_str}, {self._user_name}!"
        return f"It's {time_str}!"

    def _handle_date_query(self) -> str:
        """Handle date query intent by returning the actual system date.

        Returns:
            Response text with current date.
        """
        now = datetime.now()
        # Format: "Today is Tuesday, January 14th, 2025"
        day_name = now.strftime("%A")
        month_name = now.strftime("%B")
        day = now.day
        year = now.year

        # Add ordinal suffix
        suffix = "th" if 10 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        return f"Today is {day_name}, {month_name} {day}{suffix}, {year}."

    def _handle_future_time_query(self, intent: Intent) -> str:
        """Handle future time query intent by calculating the time offset.

        Args:
            intent: Classified intent with amount and unit entities.

        Returns:
            Response text with calculated future time.
        """
        amount_str = intent.entities.get("amount", "1")
        unit = intent.entities.get("unit", "hour")

        try:
            amount = int(amount_str)
        except ValueError:
            amount = 1

        now = datetime.now()

        # Calculate the future time
        if unit in ("hour", "hr"):
            future = now + timedelta(hours=amount)
        else:  # minute, min
            future = now + timedelta(minutes=amount)

        # Format the future time
        time_str = future.strftime("%-I:%M %p")

        # Construct warm response
        if amount == 1:
            unit_name = "hour" if unit in ("hour", "hr") else "minute"
            return f"In {amount} {unit_name}, it'll be {time_str}!"
        else:
            unit_name = "hours" if unit in ("hour", "hr") else "minutes"
            return f"In {amount} {unit_name}, it'll be {time_str}!"

    def _on_timer_expire(self, timer: "Timer") -> None:
        """Callback when a timer expires."""
        # Skip if this timer is being handled by countdown
        # Don't delete the entry - let the countdown finish first
        if timer.id in self._countdown_active:
            logger.debug(f"Timer {timer.id} being handled by countdown, skipping callback")
            return

        logger.info(f"Timer expired: {timer.name or 'unnamed'}")
        if self._feedback:
            self._feedback.play(FeedbackType.TIMER_ALERT)

        # Announce the timer
        if timer.name:
            message = f"Your timer '{timer.name}' has finished."
        else:
            message = "Your timer has finished."

        if self._synthesizer and self._playback:
            try:
                synthesis_result = self._synthesizer.synthesize(message)
                self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            except Exception as e:
                logger.error(f"Failed to announce timer: {e}")

    def _on_reminder_trigger(self, reminder: "Reminder") -> None:
        """Callback when a reminder triggers."""
        # Skip if this reminder is being handled by countdown
        # Don't delete the entry - let the countdown finish first
        if reminder.id in self._countdown_active:
            logger.debug(f"Reminder {reminder.id} being handled by countdown, skipping callback")
            return

        logger.info(f"Reminder triggered: {reminder.message}")
        if self._feedback:
            self._feedback.play(FeedbackType.REMINDER_ALERT)

        # Announce the reminder
        message = f"Reminder: {reminder.message}"

        if self._synthesizer and self._playback:
            try:
                synthesis_result = self._synthesizer.synthesize(message)
                self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            except Exception as e:
                logger.error(f"Failed to announce reminder: {e}")

    def _get_countdown_start(self, remaining_seconds: float) -> int:
        """Get the starting number for countdown based on remaining time.

        Args:
            remaining_seconds: Seconds until reminder triggers.

        Returns:
            Starting countdown number (1-5).
        """
        if remaining_seconds <= 1:
            return 1
        return min(5, int(remaining_seconds))

    def _get_upcoming_reminders(self, seconds: int) -> list[Reminder]:
        """Find reminders that will trigger within the given time window.

        Args:
            seconds: Time window in seconds.

        Returns:
            List of reminders within the window, excluding those already in countdown.
        """
        now = datetime.now(UTC)
        window_end = now + timedelta(seconds=seconds)

        upcoming = []
        for reminder in self._reminder_manager.list_pending():
            # Skip if already in countdown
            if reminder.id in self._countdown_active:
                continue

            # Check if within window
            if now <= reminder.remind_at <= window_end:
                upcoming.append(reminder)

        return sorted(upcoming, key=lambda r: r.remind_at)

    def _get_upcoming_timers(self, seconds: int) -> list[Timer]:
        """Find timers that will expire within the given time window.

        Args:
            seconds: Time window in seconds.

        Returns:
            List of timers within the window, excluding those already in countdown.
        """
        now = datetime.now(UTC)
        window_end = now + timedelta(seconds=seconds)

        upcoming = []
        for timer in self._timer_manager.list_active():
            # Skip if already in countdown
            if timer.id in self._countdown_active:
                continue

            # Check if within window
            if now <= timer.expires_at <= window_end:
                upcoming.append(timer)

        return sorted(upcoming, key=lambda t: t.expires_at)

    def _generate_countdown_phrase(self, reminders: list[Reminder], user_name: str | None) -> str:
        """Generate the countdown announcement phrase.

        Args:
            reminders: List of reminders to announce.
            user_name: User's name or None for generic greeting.

        Returns:
            Countdown phrase like "Ammar, you should start your call in"
        """
        # Use name or fallback to generic greeting
        greeting = user_name if user_name else "Hey"

        # Combine task descriptions
        if len(reminders) == 1:
            tasks = reminders[0].message
        else:
            task_list = [r.message for r in reminders]
            tasks = " and ".join(task_list)

        return f"{greeting}, you should {tasks} in"

    def _start_countdown(self, reminders: list[Reminder]) -> None:
        """Start the countdown announcement for the given reminders.

        Args:
            reminders: Reminders to count down for.
        """
        if not reminders or not self._synthesizer or not self._playback:
            return

        # Note: _countdown_in_progress is already set by the caller with the lock
        # Note: reminders are already marked in _countdown_active by the caller
        # to prevent race conditions with check_due()

        try:
            # Calculate starting number based on first reminder
            now = datetime.now(UTC)
            first_reminder = reminders[0]
            remaining = (first_reminder.remind_at - now).total_seconds()
            start_number = self._get_countdown_start(remaining)

            # Generate and speak the intro phrase
            intro = self._generate_countdown_phrase(reminders, self._user_name)
            logger.info(f"Starting countdown: {intro} {start_number}...")

            # Speak intro with first number
            try:
                intro_text = f"{intro} {start_number}"
                synthesis_result = self._synthesizer.synthesize(intro_text)
                self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            except Exception as e:
                logger.error(f"Failed to synthesize countdown intro: {e}")
                return

            # Count down from start_number-1 to 1
            for num in range(start_number - 1, 0, -1):
                # Check if any reminder was cancelled
                if not any(self._countdown_active.get(r.id, False) for r in reminders):
                    logger.info("Countdown cancelled")
                    return

                # Wait for the interval
                time.sleep(self._countdown_interval)

                # Speak the number
                try:
                    synthesis_result = self._synthesizer.synthesize(str(num))
                    self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
                except Exception as e:
                    logger.error(f"Failed to synthesize countdown number {num}: {e}")

            # Final wait and "now"
            if any(self._countdown_active.get(r.id, False) for r in reminders):
                time.sleep(self._countdown_interval)
                try:
                    synthesis_result = self._synthesizer.synthesize("now")
                    self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
                except Exception as e:
                    logger.error(f"Failed to synthesize 'now': {e}")

                # Play the reminder alert
                if self._feedback:
                    self._feedback.play(FeedbackType.REMINDER_ALERT)

                # Mark reminders as triggered so check_due doesn't announce again
                for reminder in reminders:
                    reminder.status = ReminderStatus.TRIGGERED
                    reminder.triggered_at = datetime.now(UTC)
                self._reminder_manager._save()

        finally:
            # Use lock when resetting state
            with self._countdown_lock:
                self._countdown_in_progress = False
                # Clean up tracking entries now that countdown is complete
                for reminder in reminders:
                    if reminder.id in self._countdown_active:
                        del self._countdown_active[reminder.id]

    def _generate_timer_countdown_phrase(self, timers: list[Timer], user_name: str | None) -> str:
        """Generate the countdown announcement phrase for timers.

        Args:
            timers: List of timers to announce.
            user_name: User's name or None for generic greeting.

        Returns:
            Countdown phrase like "Ammar, your timer ends in"
        """
        # Use name or fallback to generic greeting
        greeting = user_name if user_name else "Hey"

        if len(timers) == 1:
            timer = timers[0]
            if timer.name:
                return f"{greeting}, your {timer.name} timer ends in"
            return f"{greeting}, your timer ends in"
        else:
            return f"{greeting}, your timers end in"

    def _start_timer_countdown(self, timers: list[Timer]) -> None:
        """Start the countdown announcement for the given timers.

        Args:
            timers: Timers to count down for.
        """
        if not timers or not self._synthesizer or not self._playback:
            return

        # Note: _countdown_in_progress is already set by the caller with the lock
        # Note: timers are already marked in _countdown_active by the caller
        # to prevent race conditions with check_expired()

        try:
            # Calculate starting number based on first timer
            now = datetime.now(UTC)
            first_timer = timers[0]
            remaining = (first_timer.expires_at - now).total_seconds()
            start_number = self._get_countdown_start(remaining)

            # Generate and speak the intro phrase
            intro = self._generate_timer_countdown_phrase(timers, self._user_name)
            logger.info(f"Starting timer countdown: {intro} {start_number}...")

            # Speak intro with first number
            try:
                intro_text = f"{intro} {start_number}"
                synthesis_result = self._synthesizer.synthesize(intro_text)
                self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
            except Exception as e:
                logger.error(f"Failed to synthesize timer countdown intro: {e}")
                return

            # Count down from start_number-1 to 1
            for num in range(start_number - 1, 0, -1):
                # Check if any timer was cancelled
                if not any(self._countdown_active.get(t.id, False) for t in timers):
                    logger.info("Timer countdown cancelled")
                    return

                # Wait for the interval
                time.sleep(self._countdown_interval)

                # Speak the number
                try:
                    synthesis_result = self._synthesizer.synthesize(str(num))
                    self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
                except Exception as e:
                    logger.error(f"Failed to synthesize countdown number {num}: {e}")

            # Final wait and announcement
            if any(self._countdown_active.get(t.id, False) for t in timers):
                time.sleep(self._countdown_interval)
                try:
                    # Announce timer completion
                    if len(timers) == 1 and timers[0].name:
                        message = f"Your {timers[0].name} timer is done!"
                    else:
                        message = "Your timer is done!"
                    synthesis_result = self._synthesizer.synthesize(message)
                    self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
                except Exception as e:
                    logger.error(f"Failed to synthesize timer completion: {e}")

                # Play the timer alert
                if self._feedback:
                    self._feedback.play(FeedbackType.TIMER_ALERT)

                # Mark timers as completed so check_expired doesn't announce again
                for timer in timers:
                    timer.status = TimerStatus.COMPLETED
                    timer.alert_played = True

        finally:
            # Use lock when resetting state
            with self._countdown_lock:
                self._countdown_in_progress = False
                # Clean up tracking entries now that countdown is complete
                for timer in timers:
                    if timer.id in self._countdown_active:
                        del self._countdown_active[timer.id]

    def _wait_for_wake_word(self) -> bool:
        """Wait for wake word detection.

        Returns:
            True if wake word detected
        """
        if not self._capture or not self._wake_word:
            return False

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
        if not self._capture:
            return b""

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

    def _record_follow_up(self, timeout_ms: int = 5000) -> bytes:
        """Record follow-up speech for a limited time.

        This is used after a response ends with a question to capture
        the user's follow-up without requiring a wake word.

        Args:
            timeout_ms: Maximum time to wait for speech (default 5 seconds)

        Returns:
            Recorded audio bytes, or empty if no speech detected
        """
        if not self._capture:
            return b""

        audio_buffer = b""
        silence_start: float | None = None
        recording_start = time.time()
        speech_detected = False

        # Small delay to avoid PyAudio segfault from rapid stop/start
        time.sleep(0.1)
        self._capture.start()

        try:
            for chunk in self._capture.stream():
                audio_buffer += chunk.data

                # Check for silence (simple energy-based detection)
                energy = self._calculate_energy(chunk.data)
                is_silence = energy < 500  # Threshold

                if not is_silence:
                    speech_detected = True
                    silence_start = None
                elif speech_detected:
                    # Only track silence after speech has been detected
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) * 1000 > self._silence_timeout_ms:
                        logger.debug("Follow-up silence detected, stopping")
                        break

                # Check timeout
                if (time.time() - recording_start) * 1000 > timeout_ms:
                    logger.debug("Follow-up timeout reached")
                    break

        finally:
            self._capture.stop()

        # Only return audio if speech was detected
        if speech_detected:
            return audio_buffer
        return b""

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

        return float(rms)

    def start(self) -> None:
        """Start the voice loop in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # Start timer/reminder check thread
        self._check_thread = threading.Thread(target=self._check_timers_and_reminders, daemon=True)
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
                # Check for upcoming timers that need countdown (5-second window)
                # Use lock to make check-and-set atomic
                with self._countdown_lock:
                    if not self._countdown_in_progress:
                        upcoming_timers = self._get_upcoming_timers(5)
                        if upcoming_timers:
                            # Mark as being counted down BEFORE starting thread
                            # to prevent race condition with check_expired()
                            for timer in upcoming_timers:
                                self._countdown_active[timer.id] = True
                            self._countdown_in_progress = True
                            # Start countdown in a separate thread to not block
                            countdown_thread = threading.Thread(
                                target=self._start_timer_countdown,
                                args=(upcoming_timers,),
                                daemon=True,
                            )
                            countdown_thread.start()

                # Check for expired timers (for any not handled by countdown)
                self._timer_manager.check_expired()

                # Check for upcoming reminders that need countdown (5-second window)
                # Use lock to make check-and-set atomic
                with self._countdown_lock:
                    if not self._countdown_in_progress:
                        upcoming_reminders = self._get_upcoming_reminders(5)
                        if upcoming_reminders:
                            # Mark as being counted down BEFORE starting thread
                            # to prevent race condition with check_due()
                            for reminder in upcoming_reminders:
                                self._countdown_active[reminder.id] = True
                            self._countdown_in_progress = True
                            # Start countdown in a separate thread to not block
                            countdown_thread = threading.Thread(
                                target=self._start_countdown,
                                args=(upcoming_reminders,),
                                daemon=True,
                            )
                            countdown_thread.start()

                # Check for due reminders
                self._reminder_manager.check_due()

            except Exception as e:
                logger.error(f"Error checking timers/reminders: {e}")

            # Check every second
            time.sleep(1)


__all__ = ["InteractionResult", "Orchestrator"]
