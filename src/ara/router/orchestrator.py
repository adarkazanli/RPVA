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
from ..commands.time_query import TimeQueryCommandHandler
from ..commands.timer import Timer, TimerManager, TimerStatus, parse_duration
from ..config.loader import get_reminders_path
from ..config.personality import get_default_personality
from ..config.user_profile import load_user_profile
from ..digest.daily import DailyDigestGenerator
from ..digest.insights import InsightGenerator
from ..digest.weekly import WeeklyDigestGenerator
from ..feedback import FeedbackType
from ..notes.categorizer import categorize
from ..search import create_search_client
from .intent import Intent, IntentClassifier, IntentType
from .interrupt import InterruptManager
from .query_router import (
    FALLBACK_CAVEAT,
    NOT_FOUND_MESSAGES,
    DataSource,
    QueryRouter,
    QueryType,
    RoutingDecision,
)

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
        self._query_router = QueryRouter()
        self._timer_manager = TimerManager(on_expire=self._on_timer_expire)
        self._reminder_manager = ReminderManager(
            on_trigger=self._on_reminder_trigger,
            persistence_path=get_reminders_path(),
        )

        # System command handler (if mode manager is provided)
        self._system_handler = SystemCommandHandler(mode_manager) if mode_manager else None

        # Time query handler (initialized without storage by default)
        # Can be set later via set_time_query_storage() when MongoDB is available
        self._time_query_handler = TimeQueryCommandHandler(storage=None)

        # Interaction storage (for logging all interactions to MongoDB)
        self._interaction_storage: object | None = None

        # Note and activity repositories (set via set_note_storage)
        self._note_repository: object | None = None
        self._activity_repository: object | None = None
        self._activity_data_source: object | None = None
        self._note_data_source: object | None = None
        self._entity_extractor: object | None = None

        # Background check thread for timers/reminders
        self._check_thread: threading.Thread | None = None

        # Recording configuration - default (questions/commands)
        self._silence_timeout_ms = 2000  # Stop recording after 2s silence
        self._max_recording_ms = 10000  # Max 10s recording

        # Recording configuration - note-taking mode (patient, no interruption)
        self._note_silence_timeout_ms = 10000  # 10s silence for notes (user can pause to think)
        self._note_max_recording_ms = 180000  # 3 minute max for notes
        self._note_trigger_phrases = ["take note", "take a note", "note that", "remember that"]
        self._stop_keyword = "porcupine"  # Say wake word to end note recording early

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

        # Initialize interrupt manager for speech interrupt handling
        self._interrupt_manager: InterruptManager | None = None
        if audio_capture and audio_playback and transcriber:
            self._interrupt_manager = InterruptManager(
                capture=audio_capture,
                playback=audio_playback,
                transcriber=transcriber,
            )
            logger.info("Interrupt manager initialized")

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

            # Step 2: Record user speech with mode detection
            stt_start = time.time()
            audio_data, is_note_mode = self._record_with_mode_detection()

            if not audio_data:
                logger.warning("No speech detected")
                return None

            # Step 3: Transcribe speech (full audio for note mode)
            transcript_result = self._transcriber.transcribe(audio_data, 16000)
            transcript = transcript_result.text.strip()

            # Strip stop keyword if present (case-insensitive) - only for note mode
            if is_note_mode and transcript.lower().endswith(self._stop_keyword):
                transcript = transcript[: -len(self._stop_keyword)].strip()
                # Also handle punctuation before the keyword
                transcript = transcript.rstrip(".,;:!?")
                logger.info("Stop keyword detected, stripped from transcript")

            if not transcript:
                logger.warning("Empty transcription")
                return None

            latencies["stt_ms"] = int((time.time() - stt_start) * 1000)
            logger.info(f"Transcribed: '{transcript}' (note_mode={is_note_mode})")

            # Log capture timing
            _log_interaction_timing("captured", transcript)

            # Step 4: Classify intent (or force NOTE_CAPTURE for note mode)
            if is_note_mode:
                # Force note capture intent for note-taking mode
                from .intent import Intent, IntentType

                intent = Intent(
                    type=IntentType.NOTE_CAPTURE,
                    confidence=1.0,
                    entities={"content": transcript},
                )
                logger.info("Note mode: forcing NOTE_CAPTURE intent")
            else:
                intent = self._intent_classifier.classify(transcript)
            logger.info(f"Intent: {intent.type.value} (confidence: {intent.confidence:.2f})")

            # Step 5: Handle intent (command or LLM)
            response_start = time.time()
            response_text = self._handle_intent(intent, interaction_id)
            latencies["llm_ms"] = int((time.time() - response_start) * 1000)
            logger.info(f"Response: '{response_text[:50]}...'")

            # Log response timing
            _log_interaction_timing("responded", response_text)

            # Step 6: Synthesize speech (brief confirmation for note mode)
            tts_start = time.time()
            if is_note_mode:
                # Brief confirmation for notes - no need to repeat content
                brief_response = "Noted."
                synthesis_result = self._synthesizer.synthesize(brief_response)
            else:
                synthesis_result = self._synthesizer.synthesize(response_text)
            latencies["tts_ms"] = int((time.time() - tts_start) * 1000)

            # Step 7: Play response with interrupt monitoring
            play_start = time.time()

            # Use interrupt manager for non-note responses
            if self._interrupt_manager and not is_note_mode:
                # Store original request for potential reprocessing
                self._interrupt_manager.reset()
                self._interrupt_manager.set_initial_request(transcript)

                # Play with monitoring for user speech
                interrupt_event = self._interrupt_manager.play_with_monitoring(
                    synthesis_result.audio,
                    synthesis_result.sample_rate,
                )

                if interrupt_event:
                    # Interrupt detected - handle reprocessing
                    logger.info("User interrupt detected, processing...")
                    latencies["play_ms"] = int((time.time() - play_start) * 1000)

                    # Play acknowledgment tone
                    if self._feedback:
                        self._feedback.play(FeedbackType.INTERRUPT_ACKNOWLEDGED)

                    # Wait for user to finish speaking
                    interrupt_text = self._interrupt_manager.wait_for_interrupt_complete()
                    if interrupt_text:
                        logger.info(f"Interrupt text: '{interrupt_text}'")

                        # Only respond to explicit interrupt keywords (stop, wait)
                        # Ignore noise and other speech to reduce false positives
                        stop_keywords = {"stop"}  # Full stop, end interaction
                        wait_keywords = {"wait", "hold on"}  # Pause, add context, reprocess

                        text_lower = interrupt_text.lower().strip()

                        if text_lower in stop_keywords:
                            # Full stop - end interaction immediately
                            logger.info("Stop keyword - ending interaction")
                            response_text = "OK."
                            if self._synthesizer:
                                synth = self._synthesizer.synthesize(response_text)
                                self._playback.play(synth.audio, synth.sample_rate)
                            transcript = interrupt_text
                            self._interrupt_manager.reset()
                        elif text_lower in wait_keywords:
                            # Wait for more context to add to original request
                            logger.info("Wait keyword - prompting for context")
                            clarification = "Go ahead."
                            if self._synthesizer:
                                synth = self._synthesizer.synthesize(clarification)
                                self._playback.play(synth.audio, synth.sample_rate)

                            # Wait for follow-up context (buffer preserved)
                            follow_up = self._record_follow_up(timeout_ms=10000)
                            if follow_up and self._transcriber:
                                follow_result = self._transcriber.transcribe(follow_up, 16000)
                                if follow_result.text.strip():
                                    # Add context to buffer and reprocess combined
                                    self._interrupt_manager.request_buffer.append(
                                        follow_result.text.strip(), is_interrupt=True
                                    )
                                    combined_request = self._interrupt_manager.get_combined_request()
                                    logger.info(f"Wait combined: '{combined_request}'")
                                    _log_interaction_timing("captured", combined_request)

                                    combined_intent = self._intent_classifier.classify(combined_request)
                                    combined_response = self._handle_intent(
                                        combined_intent, interaction_id
                                    )
                                    _log_interaction_timing("responded", combined_response)

                                    if self._synthesizer:
                                        combined_synth = self._synthesizer.synthesize(combined_response)
                                        self._playback.play(
                                            combined_synth.audio, combined_synth.sample_rate
                                        )

                                    transcript = combined_request
                                    response_text = combined_response
                                    intent = combined_intent
                            else:
                                transcript = interrupt_text
                                response_text = clarification
                        else:
                            # Not a recognized interrupt keyword - ignore (likely noise)
                            logger.info(f"Ignoring non-keyword interrupt: '{interrupt_text}'")
                            self._interrupt_manager.reset()
                else:
                    latencies["play_ms"] = int((time.time() - play_start) * 1000)

                    # Start continuation window for potential follow-up speech
                    continuation_result = self._handle_continuation_window(
                        interaction_id
                    )
                    if continuation_result:
                        transcript, response_text, intent = continuation_result
            else:
                # Direct playback for note mode or when interrupt manager unavailable
                self._playback.play(synthesis_result.audio, synthesis_result.sample_rate)
                latencies["play_ms"] = int((time.time() - play_start) * 1000)

            # Step 8: Check for follow-up if response ended with a question (skip for note mode)
            if not is_note_mode and response_text.strip().endswith("?"):
                logger.info("Response ended with question, listening for follow-up...")
                follow_up_audio = self._record_follow_up(timeout_ms=5000)

                if follow_up_audio:
                    # Process the follow-up
                    follow_up_result = self._transcriber.transcribe(follow_up_audio, 16000)
                    follow_up_text = follow_up_result.text.strip()

                    # Strip stop keyword if present
                    if follow_up_text.lower().endswith(self._stop_keyword):
                        follow_up_text = follow_up_text[: -len(self._stop_keyword)].strip()
                        follow_up_text = follow_up_text.rstrip(".,;:!?")

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

            # Log the interaction to file logger
            if self._interaction_logger:
                latencies["total"] = total_latency
                self._interaction_logger.log(
                    transcript=transcript,
                    response=response_text,
                    intent=intent.type.value,
                    latency_ms=latencies,
                    entities=intent.entities,
                )

            # Log interaction to MongoDB
            if self._interaction_storage is not None:
                try:
                    from datetime import UTC, datetime

                    from ..storage.models import InteractionDTO

                    mongo_interaction = InteractionDTO(
                        session_id=str(interaction_id),
                        timestamp=datetime.now(UTC),
                        device_id="voice-agent",
                        transcript=transcript,
                        transcript_confidence=transcript_result.confidence
                        if hasattr(transcript_result, "confidence")
                        else 1.0,
                        intent_type=intent.type.value,
                        intent_confidence=intent.confidence,
                        response_text=response_text,
                        response_source="local",
                        latency_ms=latencies,
                        entities=intent.entities,
                    )
                    self._interaction_storage.interactions.save(mongo_interaction)  # type: ignore
                    logger.debug("Interaction saved to MongoDB")
                except Exception as e:
                    logger.warning(f"Failed to log interaction to MongoDB: {e}")

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
        from datetime import UTC, datetime

        interaction_id = uuid.uuid4()
        intent = self._intent_classifier.classify(text)
        response = self._handle_intent(intent, interaction_id)

        # Log interaction to MongoDB if storage is available
        if self._interaction_storage is not None:
            try:
                from ..storage.models import InteractionDTO

                interaction = InteractionDTO(
                    session_id=str(uuid.uuid4()),  # TODO: track session properly
                    timestamp=datetime.now(UTC),
                    device_id="voice-agent",
                    transcript=text,
                    transcript_confidence=1.0,
                    intent_type=intent.type.value,
                    intent_confidence=intent.confidence,
                    response_text=response,
                    response_source="local",
                    latency_ms={},
                    entities=intent.entities,
                )
                self._interaction_storage.interactions.save(interaction)  # type: ignore
            except Exception as e:
                logger.warning(f"Failed to log interaction: {e}")

        return response

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
        elif intent.type == IntentType.DURATION_QUERY:
            return self._handle_duration_query(intent)
        elif intent.type == IntentType.ACTIVITY_SEARCH:
            return self._handle_activity_search(intent)
        elif intent.type == IntentType.EVENT_LOG:
            return self._handle_event_log(intent, interaction_id)
        # Note-taking & time tracking intents (005-time-tracking-notes)
        elif intent.type == IntentType.NOTE_CAPTURE:
            return self._handle_note_capture(intent)
        elif intent.type == IntentType.NOTE_QUERY:
            return self._handle_note_query(intent)
        elif intent.type == IntentType.ACTIVITY_START:
            return self._handle_activity_start(intent)
        elif intent.type == IntentType.ACTIVITY_STOP:
            return self._handle_activity_stop(intent)
        elif intent.type == IntentType.DIGEST_DAILY:
            return self._handle_digest_daily(intent)
        elif intent.type == IntentType.DIGEST_WEEKLY:
            return self._handle_digest_weekly(intent)
        elif intent.type == IntentType.ACTION_ITEMS_QUERY:
            return self._handle_action_items(intent)
        elif intent.type == IntentType.EMAIL_ACTION_ITEMS:
            return self._handle_email_action_items(intent)
        else:
            # Use QueryRouter for smart routing of general questions
            routing_decision = self._query_router.classify(intent.raw_text)
            logger.debug(
                f"QueryRouter decision: {routing_decision.query_type.value} -> "
                f"{routing_decision.primary_source.value} "
                f"(confidence: {routing_decision.confidence:.2f})"
            )

            # Route based on query type
            if routing_decision.query_type == QueryType.PERSONAL_DATA:
                return self._handle_personal_query(intent, routing_decision)
            elif routing_decision.query_type == QueryType.FACTUAL_CURRENT:
                return self._handle_factual_query(intent, routing_decision)
            else:
                # GENERAL_KNOWLEDGE or default - use LLM
                return self._handle_general_knowledge_query(intent)

    def _handle_personal_query(self, intent: Intent, _routing_decision: RoutingDecision) -> str:
        """Handle personal data query by checking MongoDB first.

        Routes queries about user's personal data (activities, history, notes)
        to MongoDB. Returns "not found" message if no data exists - never
        falls back to LLM to prevent hallucination of personal information.

        Args:
            intent: Classified intent with raw query text.
            _routing_decision: Routing decision from QueryRouter (reserved for future use).

        Returns:
            Response text with personal data or "not found" message.
        """
        query = intent.raw_text.lower()

        # Try to query MongoDB for personal data
        if self._interaction_storage is not None:
            try:
                # Search interactions collection for relevant data
                collection = self._interaction_storage.interactions._collection  # type: ignore
                docs = list(collection.find().sort("timestamp", -1).limit(50))

                # Look for relevant entries based on query content
                for doc in docs:
                    transcript = doc.get("input", {}).get("transcript", "")
                    # Simple keyword matching for now
                    if any(word in transcript.lower() for word in query.split() if len(word) > 3):
                        # Found potentially relevant data
                        ts = doc.get("timestamp")
                        if ts:
                            time_diff = datetime.now(UTC) - ts
                            minutes = int(time_diff.total_seconds() / 60)
                            if minutes < 60:
                                return f"I found a related entry from {minutes} minutes ago: {transcript[:100]}..."
                            else:
                                hours = minutes // 60
                                return f"I found a related entry from {hours} hours ago: {transcript[:100]}..."

                logger.debug("No matching personal data found in MongoDB")
            except Exception as e:
                logger.warning(f"Failed to query MongoDB for personal data: {e}")
                return NOT_FOUND_MESSAGES.get("default", "I don't have any records of that.")

        # Determine appropriate "not found" message based on query content
        if "exercise" in query or "workout" in query or "gym" in query:
            return NOT_FOUND_MESSAGES.get("exercise", NOT_FOUND_MESSAGES["default"])
        elif "meeting" in query:
            return NOT_FOUND_MESSAGES.get("meeting", NOT_FOUND_MESSAGES["default"])
        elif "mention" in query or "said" in query or "asked" in query:
            return NOT_FOUND_MESSAGES.get("mention", NOT_FOUND_MESSAGES["default"])
        else:
            return NOT_FOUND_MESSAGES.get("default", "I don't have any records of that.")

    def _handle_factual_query(self, intent: Intent, routing_decision: RoutingDecision) -> str:
        """Handle factual/time-sensitive query using web search.

        Routes queries about verifiable facts (weather, prices, news, distances)
        to web search first. Falls back to LLM with caveat if search fails.

        Args:
            intent: Classified intent with raw query text.
            routing_decision: Routing decision from QueryRouter.

        Returns:
            Response text with factual data or fallback response with caveat.
        """
        query = intent.raw_text.strip().rstrip("?!.")

        try:
            # Use web search for factual queries
            result = self._search_client.search(query, max_results=3, include_answer=True)

            if result.success and result.answer:
                # Direct answer from search
                answer = result.answer
                if len(answer) > 250:
                    answer = answer[:247] + "..."

                # Add user name greeting if available
                if self._user_name:
                    return f"{self._user_name}, {answer}"
                return answer

            if result.success and result.results:
                # Summarize search results
                summaries = []
                for r in result.results[:3]:
                    content = r.get("content", "")
                    if content:
                        summaries.append(content[:80])

                if summaries:
                    combined = " ".join(summaries)
                    if len(combined) > 250:
                        combined = combined[:247] + "..."

                    if self._user_name:
                        return f"{self._user_name}, {combined}"
                    return combined

            # Search succeeded but no useful results - fall back to LLM with caveat
            logger.info("Web search returned no useful results, falling back to LLM with caveat")

        except Exception as e:
            logger.warning(f"Web search failed: {e}, falling back to LLM with caveat")

        # Fallback to LLM with caveat (if enabled in routing decision)
        if routing_decision.fallback_source == DataSource.LLM and self._llm:
            llm_response = self._llm.generate(intent.raw_text)
            response_text = llm_response.text.strip()

            # Add caveat prefix if routing decision says we should
            if routing_decision.should_caveat:
                return f"{FALLBACK_CAVEAT}{response_text}"
            return response_text

        return "I couldn't find that information right now."

    def _handle_general_knowledge_query(self, intent: Intent) -> str:
        """Handle general knowledge query using LLM directly.

        Routes queries about static knowledge (definitions, how-to, math)
        directly to the LLM for fast responses.

        Args:
            intent: Classified intent with raw query text.

        Returns:
            Response text from LLM.
        """
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
        from datetime import UTC

        query_type = intent.entities.get("query_type", "list")
        search_content = intent.entities.get("search_content", "")
        time_ref = intent.entities.get("time_ref", "recent")

        # Try MongoDB first (preferred)
        entries: list[dict[str, datetime | str]] = []
        if self._interaction_storage is not None:
            try:
                # Query recent interactions from MongoDB
                collection = self._interaction_storage.interactions._collection  # type: ignore
                docs = list(collection.find().sort("timestamp", -1).limit(100))
                for doc in docs:
                    ts = doc.get("timestamp")
                    # Ensure timezone awareness
                    if ts and ts.tzinfo is None:
                        ts = ts.replace(tzinfo=UTC)
                    transcript = doc.get("input", {}).get("transcript", "")
                    if ts and transcript:
                        entries.append({"timestamp": ts, "content": transcript})
                logger.debug(f"Loaded {len(entries)} entries from MongoDB")
            except Exception as e:
                logger.warning(f"Failed to query MongoDB for history: {e}")

        # Fall back to text file if MongoDB not available or empty
        if not entries:
            log_file = _INTERACTION_LOG_FILE
            if log_file.exists():
                try:
                    with open(log_file) as f:
                        lines = f.readlines()
                    for line in lines:
                        if "captured ->" in line:
                            try:
                                timestamp_str = (
                                    line.split(":")[0]
                                    + ":"
                                    + line.split(":")[1]
                                    + ":"
                                    + line.split(":")[2]
                                )
                                timestamp = datetime.strptime(
                                    timestamp_str.strip(), "%Y-%m-%d %H:%M:%S"
                                )
                                content = line.split('-> "')[1].rstrip('"\n')
                                entries.append({"timestamp": timestamp, "content": content})
                            except (IndexError, ValueError):
                                continue
                except Exception as e:
                    logger.error(f"Failed to read interaction log: {e}")

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
            now = datetime.now(UTC)

            # Entries from MongoDB are already sorted most-recent-first
            for entry in entries:
                entry_content = str(entry["content"])
                entry_timestamp = entry["timestamp"]
                if not isinstance(entry_timestamp, datetime):
                    continue
                # Skip the current query itself (avoid matching "asked about X" with itself)
                if (
                    "asked" in entry_content.lower()
                    and search_content.lower()[:20] in entry_content.lower()
                ):
                    continue
                if fuzzy_match(search_content, entry_content):
                    # Ensure timezone awareness for comparison
                    if entry_timestamp.tzinfo is None:
                        entry_timestamp = entry_timestamp.replace(tzinfo=UTC)
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
            now = datetime.now(UTC)
            for entry in entries:  # Already sorted most-recent-first
                entry_content = str(entry["content"])
                entry_timestamp = entry["timestamp"]
                if not isinstance(entry_timestamp, datetime):
                    continue
                if fuzzy_match(search_content, entry_content):
                    if entry_timestamp.tzinfo is None:
                        entry_timestamp = entry_timestamp.replace(tzinfo=UTC)
                    time_diff = now - entry_timestamp
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

    def _handle_duration_query(self, intent: Intent) -> str:
        """Handle duration query intent ('how long was I...').

        Args:
            intent: Classified intent with activity entity.

        Returns:
            Response text with duration information.
        """
        activity = intent.entities.get("activity", "")
        if not activity:
            return "What activity would you like to know the duration of?"

        return self._time_query_handler.handle_duration_query(activity)

    def _handle_activity_search(self, intent: Intent) -> str:
        """Handle activity search intent ('what was I doing around...').

        Args:
            intent: Classified intent with time reference entities.

        Returns:
            Response text with activities found.
        """
        time_ref = intent.entities.get("time_ref")
        start_time = intent.entities.get("start_time")
        end_time = intent.entities.get("end_time")

        return self._time_query_handler.handle_activity_search(
            time_ref=time_ref,
            start_time=start_time,
            end_time=end_time,
        )

    def _handle_event_log(self, intent: Intent, interaction_id: uuid.UUID) -> str:
        """Handle event log intent ('I'm going to the gym').

        Args:
            intent: Classified intent with context and event_type entities.
            interaction_id: ID of the current interaction.

        Returns:
            Response text confirming the logged event.
        """
        context = intent.entities.get("context", "")
        event_type = intent.entities.get("event_type", "note")

        if not context:
            return "I didn't catch what you wanted to log."

        return self._time_query_handler.handle_event_log(
            context=context,
            event_type=event_type,
            interaction_id=str(interaction_id),
        )

    # --- Note-taking & time tracking handlers (005-time-tracking-notes) ---

    def _handle_note_capture(self, intent: Intent) -> str:
        """Handle note capture intent ('note that...', 'remember...').

        Args:
            intent: Classified intent with content entity.

        Returns:
            Response confirming note was captured with action items.
        """
        from ..storage.models import NoteDTO

        content = intent.entities.get("content", intent.raw_text)

        if not content:
            return "What would you like me to note?"

        logger.info(f"Note captured: {content[:50]}...")

        # Extract entities and categorize if storage is available
        action_items: list[str] = []
        if self._note_repository:
            # Auto-categorize the note
            category = categorize(content)

            # Extract entities (people, topics, locations, action_items) if extractor available
            people: list[str] = []
            topics: list[str] = []
            locations: list[str] = []

            if self._entity_extractor:
                try:
                    entities = self._entity_extractor.extract(content)  # type: ignore
                    people = entities.people
                    topics = entities.topics
                    locations = entities.locations
                    action_items = entities.action_items
                except Exception as e:
                    logger.warning(f"Entity extraction failed: {e}")

            # Save to MongoDB
            note = NoteDTO(
                transcript=content,
                category=category.value,
                timestamp=datetime.now(UTC),
                user_id="default",
                people=people,
                topics=topics,
                locations=locations,
                action_items=action_items,
            )
            note_id = self._note_repository.save(note)  # type: ignore
            logger.info(f"Note saved with id={note_id}, category={category.value}")
            if action_items:
                logger.info(f"Action items extracted: {action_items}")

        # Build response with action items
        return self._build_note_response(action_items)

    def _build_note_response(self, action_items: list[str]) -> str:
        """Build confirmation response for note capture.

        Args:
            action_items: List of extracted action items.

        Returns:
            Response string with action items mentioned.
        """
        name = self._user_name or ""
        greeting = f"Got it{', ' + name if name else ''}!"

        if not action_items:
            return f"{greeting} Noted."

        # Format action items for speech
        if len(action_items) == 1:
            return f"{greeting} Noted. I'll add '{action_items[0]}' to your action items for today."
        elif len(action_items) == 2:
            return (
                f"{greeting} Noted. I'll add '{action_items[0]}' and "
                f"'{action_items[1]}' to your action items."
            )
        else:
            # Multiple items - summarize
            return (
                f"{greeting} Noted. I found {len(action_items)} action items "
                f"including '{action_items[0]}'. All added to your list."
            )

    def _handle_note_query(self, intent: Intent) -> str:
        """Handle note query intent ('what did I discuss with...').

        Args:
            intent: Classified intent with search_term entity.

        Returns:
            Response with matching notes or 'no results' message.
        """
        search_term = intent.entities.get("search_term", "")

        if not search_term:
            return "Who or what would you like me to search for in your notes?"

        logger.info(f"Note query: searching for '{search_term}'")

        if not self._note_repository:
            return f"I don't have any notes mentioning {search_term} yet."

        # Search by person first, then by topic, then full-text
        notes = self._note_repository.find_by_person(search_term)  # type: ignore
        if not notes:
            notes = self._note_repository.find_by_topic(search_term)  # type: ignore
        if not notes:
            notes = self._note_repository.search_text(search_term)  # type: ignore

        if not notes:
            return f"I don't have any notes mentioning {search_term} yet."

        # Format response with found notes
        if len(notes) == 1:
            note = notes[0]
            return f"I found one note: {note.transcript[:100]}..."

        # Multiple notes - summarize
        response = f"I found {len(notes)} notes mentioning {search_term}. "
        response += f"Most recent: {notes[0].transcript[:80]}..."
        return response

    def _handle_activity_start(self, intent: Intent) -> str:
        """Handle activity start intent ('starting my workout').

        Args:
            intent: Classified intent with activity entity.

        Returns:
            Response confirming activity started.
        """
        from ..storage.models import TimeTrackingActivityDTO

        activity = intent.entities.get("activity", "")

        if not activity:
            return "What activity are you starting?"

        logger.info(f"Activity started: {activity}")

        response_parts = []

        if self._activity_repository:
            # Check for and close any active activity
            active = self._activity_repository.get_active()  # type: ignore
            if active:
                # Close the previous activity
                active.end_time = datetime.now(UTC)
                active.status = "completed"
                if active.start_time:
                    delta = active.end_time - active.start_time
                    active.duration_minutes = int(delta.total_seconds() / 60)
                self._activity_repository.update(active)  # type: ignore
                response_parts.append(
                    f"Stopped {active.name} ({active.duration_minutes or 0} minutes)."
                )

            # Categorize and start new activity
            category = categorize(activity)

            new_activity = TimeTrackingActivityDTO(
                name=activity,
                category=category.value,
                start_time=datetime.now(UTC),
                status="active",
                user_id="default",
            )
            activity_id = self._activity_repository.save(new_activity)  # type: ignore
            logger.info(f"Activity saved with id={activity_id}, category={category.value}")

        # Concise confirmation
        if self._user_name:
            response_parts.append(f"Started tracking {activity}, {self._user_name}!")
        else:
            response_parts.append(f"Started tracking {activity}!")

        return " ".join(response_parts)

    def _handle_activity_stop(self, intent: Intent) -> str:
        """Handle activity stop intent ('done with workout').

        Args:
            intent: Classified intent with activity entity.

        Returns:
            Response confirming activity stopped with duration.
        """
        activity_name = intent.entities.get("activity", "")

        logger.info(f"Activity stopped: {activity_name if activity_name else 'current'}")

        if not self._activity_repository:
            if activity_name:
                return f"Stopped tracking {activity_name}."
            return "Stopped tracking your activity."

        # Get active activity
        active = self._activity_repository.get_active()  # type: ignore

        if not active:
            return "You don't have any active activity to stop."

        # Just stop the current activity - user knows what they're working on
        # No need to require exact name match (they may describe it differently)

        # Complete the activity
        active.end_time = datetime.now(UTC)
        active.status = "completed"
        if active.start_time:
            delta = active.end_time - active.start_time
            active.duration_minutes = int(delta.total_seconds() / 60)

        self._activity_repository.update(active)  # type: ignore

        # Format duration for response
        duration = active.duration_minutes or 0
        if duration >= 60:
            hours = duration // 60
            mins = duration % 60
            duration_str = f"{hours} hour{'s' if hours > 1 else ''}"
            if mins > 0:
                duration_str += f" and {mins} minute{'s' if mins > 1 else ''}"
        else:
            duration_str = f"{duration} minute{'s' if duration != 1 else ''}"

        return f"Stopped tracking {active.name}. Duration: {duration_str}."

    def _handle_digest_daily(self, _intent: Intent) -> str:
        """Handle daily digest intent ('how did I spend my time today?').

        Args:
            _intent: Classified intent (unused, kept for interface consistency).

        Returns:
            Response with daily time breakdown.
        """
        logger.info("Daily digest requested")

        if not self._activity_data_source and not self._note_data_source:
            return "I don't have any activities or notes tracked for today yet."

        # Generate daily digest using the data sources
        generator = DailyDigestGenerator(
            data_source=self._activity_data_source,  # type: ignore
            note_source=self._note_data_source,  # type: ignore
            user_id="default",
        )
        digest = generator.generate()

        return digest.summary

    def _handle_digest_weekly(self, _intent: Intent) -> str:
        """Handle weekly digest intent ('how did I spend my time this week?').

        Args:
            _intent: Classified intent (unused, kept for interface consistency).

        Returns:
            Response with weekly time breakdown and insights.
        """
        logger.info("Weekly digest requested")

        if not self._activity_data_source:
            return "I don't have enough activity data for a weekly summary yet."

        # Generate weekly digest
        generator = WeeklyDigestGenerator(
            data_source=self._activity_data_source,  # type: ignore
            user_id="default",
        )
        digest = generator.generate()

        # Add insights if we have enough data
        insight_gen = InsightGenerator(
            data_source=self._activity_data_source,  # type: ignore
            user_id="default",
        )
        insights = insight_gen.analyze(weeks=2)

        if insights:
            # Append first insight to summary
            return f"{digest.summary} {insights[0].description}"

        return digest.summary

    def _handle_action_items(self, intent: Intent) -> str:
        """Handle action items query intent ('what are my action items?').

        Args:
            intent: Classified intent with optional date_ref entity.

        Returns:
            Response listing action items for the specified date.
        """
        from datetime import date, timedelta

        logger.info("Action items query requested")

        if not self._note_data_source:
            return "I don't have any action items tracked yet."

        # Determine which date to query
        date_ref = intent.entities.get("date_ref", "").lower()
        if date_ref == "yesterday":
            target_date = date.today() - timedelta(days=1)
            date_label = "yesterday"
        else:
            target_date = date.today()
            date_label = "today"

        logger.info(f"Fetching action items for {date_label} ({target_date})")

        # Fetch action items from notes for the target date
        notes = self._note_data_source.get_notes_for_date(target_date, "default")

        action_items: list[str] = []
        for note in notes:
            items = note.get("action_items", [])
            action_items.extend(items)

        if not action_items:
            return f"You don't have any action items from {date_label}."

        # Build response listing all action items
        name = self._user_name or ""
        if date_label == "yesterday":
            greeting = f"Here are your action items from yesterday{', ' + name if name else ''}:"
        else:
            greeting = f"Here are your action items{', ' + name if name else ''}:"

        if len(action_items) == 1:
            return f"{greeting} {action_items[0]}."
        elif len(action_items) == 2:
            return f"{greeting} {action_items[0]}, and {action_items[1]}."
        else:
            items_list = ", ".join(action_items[:-1])
            return f"{greeting} {items_list}, and {action_items[-1]}."

    def _handle_email_action_items(self, intent: Intent) -> str:
        """Handle email action items intent ('email me my action items').

        Args:
            intent: Classified intent with optional date_ref entity.

        Returns:
            Verbal response confirming email sent or explaining failure.
        """
        from datetime import date, timedelta

        from ara.email.config import EmailConfig
        from ara.email.sender import SMTPEmailSender

        logger.info("Email action items requested")

        # Load email configuration
        config = EmailConfig.from_env()
        if config is None or not config.is_valid():
            return (
                "Email is not configured. "
                "Please set up your email settings in the configuration file."
            )

        # Determine which date to query
        date_ref = intent.entities.get("date_ref", "").lower()
        if date_ref == "yesterday":
            target_date = date.today() - timedelta(days=1)
            date_label = "yesterday"
        else:
            target_date = date.today()
            date_label = "today"

        logger.info(f"Fetching action items for {date_label} ({target_date})")

        # Check if we have note data source
        if not self._note_data_source:
            return "I don't have any action items tracked yet."

        # Fetch action items from notes
        notes = self._note_data_source.get_notes_for_date(target_date, "default")

        action_items: list[str] = []
        for note in notes:
            items = note.get("action_items", [])
            action_items.extend(items)

        if not action_items:
            if date_label == "yesterday":
                return "You don't have any action items from yesterday to send."
            return "You don't have any action items to send."

        # Send email
        sender = SMTPEmailSender(config)
        result = sender.send_action_items(action_items, date_label, target_date)

        # Return appropriate verbal response
        if result.success:
            return "Done! I've sent your action items to your email."
        elif result.error_message == "Could not authenticate with email server.":
            return (
                "I couldn't authenticate with the email server. "
                "Please check your email credentials."
            )
        elif result.error_message == "Could not connect to email server.":
            return (
                "I couldn't connect to the email server. "
                "Please check your internet connection and try again."
            )
        else:
            return "I wasn't able to send the email. Please try again later."

    def set_time_query_storage(self, storage: object) -> None:
        """Set storage for time queries (call when MongoDB is available).

        Args:
            storage: Storage object with events and activities repositories.
        """
        self._time_query_handler = TimeQueryCommandHandler(storage=storage)  # type: ignore

    def set_interaction_storage(self, storage: object) -> None:
        """Set storage for interaction logging (call when MongoDB is available).

        Args:
            storage: Storage object with interactions repository.
        """
        self._interaction_storage = storage

    def set_note_storage(
        self,
        note_repository: object,
        activity_repository: object,
        llm: object | None = None,
        paired_activities_collection: object | None = None,
    ) -> None:
        """Set storage for notes and time tracking (call when MongoDB is available).

        Args:
            note_repository: NoteRepository instance for note storage.
            activity_repository: TimeTrackingActivityRepository instance.
            llm: Optional LLM for entity extraction. Uses self._llm if not provided.
            paired_activities_collection: Optional MongoDB collection for paired
                activities (from ActivityRepository). If provided, uses this as the
                primary data source for daily/weekly digests.
        """
        from ..notes.extractor import EntityExtractor
        from ..storage.notes import (
            MongoActivityDataSource,
            MongoNoteDataSource,
            PairedActivityDataSource,
        )

        self._note_repository = note_repository
        self._activity_repository = activity_repository
        self._note_data_source = MongoNoteDataSource(note_repository)  # type: ignore

        # Use paired activities collection if provided (has existing data),
        # otherwise fall back to time tracking activities
        if paired_activities_collection is not None:
            self._activity_data_source = PairedActivityDataSource(
                paired_activities_collection  # type: ignore
            )
            logger.info("Using paired activities collection for digests")
        else:
            self._activity_data_source = MongoActivityDataSource(activity_repository)  # type: ignore

        # Set up entity extractor with LLM
        extractor_llm = llm or self._llm
        if extractor_llm:
            self._entity_extractor = EntityExtractor(llm=extractor_llm)

        logger.info("Note and activity storage configured")

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

    def _record_speech(
        self,
        silence_timeout_ms: int | None = None,
        max_recording_ms: int | None = None,
        stop_on_wake_word: bool = False,
    ) -> bytes:
        """Record user speech until silence detected.

        Args:
            silence_timeout_ms: Override silence timeout (default: self._silence_timeout_ms)
            max_recording_ms: Override max recording time (default: self._max_recording_ms)
            stop_on_wake_word: If True, stop recording when wake word is detected

        Returns:
            Recorded audio bytes
        """
        if not self._capture:
            return b""

        silence_timeout = silence_timeout_ms or self._silence_timeout_ms
        max_recording = max_recording_ms or self._max_recording_ms

        audio_buffer = b""
        silence_start: float | None = None
        recording_start = time.time()

        # Small delay to avoid PyAudio segfault from rapid stop/start
        time.sleep(0.1)
        self._capture.start()

        try:
            for chunk in self._capture.stream():
                audio_buffer += chunk.data

                # Check for wake word to stop note recording (say "porcupine" to end)
                if stop_on_wake_word and self._wake_detector:
                    wake_result = self._wake_detector.process(chunk.data)
                    if wake_result >= 0:
                        logger.info("Wake word detected during note recording, stopping")
                        break

                # Check for silence (simple energy-based detection)
                energy = self._calculate_energy(chunk.data)
                is_silence = energy < 500  # Threshold

                if is_silence:
                    if silence_start is None:
                        silence_start = time.time()
                    elif (time.time() - silence_start) * 1000 > silence_timeout:
                        # Silence timeout reached
                        logger.debug("Silence detected, stopping recording")
                        break
                else:
                    silence_start = None

                # Check max recording time
                if (time.time() - recording_start) * 1000 > max_recording:
                    logger.debug("Max recording time reached")
                    break

        finally:
            self._capture.stop()

        return audio_buffer

    def _is_note_trigger(self, text: str) -> bool:
        """Check if text starts with a note-taking trigger phrase.

        Args:
            text: Transcribed text to check

        Returns:
            True if text indicates note-taking mode
        """
        text_lower = text.lower().strip()
        return any(text_lower.startswith(phrase) for phrase in self._note_trigger_phrases)

    def _record_with_mode_detection(self) -> tuple[bytes, bool]:
        """Record speech with automatic note-taking mode detection.

        Does a quick initial recording to detect if user wants to take a note.
        If note-taking detected, continues with extended recording settings.

        Returns:
            Tuple of (audio_bytes, is_note_mode)
        """
        if not self._capture or not self._transcriber:
            return b"", False

        # Phase 1: Quick recording to detect mode (4 seconds max, 2.5s silence)
        # More lenient to allow user to say "take note" and pause briefly
        initial_audio = self._record_speech(
            silence_timeout_ms=2500,
            max_recording_ms=4000,
        )

        if not initial_audio:
            return b"", False

        # Quick transcription to detect note-taking
        initial_result = self._transcriber.transcribe(initial_audio, 16000)
        initial_text = initial_result.text.strip()

        if not initial_text:
            return initial_audio, False

        # Check if note-taking mode
        if self._is_note_trigger(initial_text):
            logger.info("Note-taking mode detected, extending recording...")
            logger.info("Say the wake word (e.g., 'porcupine') when done to end early")

            # Phase 2: Continue with extended recording (wake word stops recording)
            extended_audio = self._record_speech(
                silence_timeout_ms=self._note_silence_timeout_ms,
                max_recording_ms=self._note_max_recording_ms,
                stop_on_wake_word=True,
            )

            # Combine audio
            combined_audio = initial_audio + extended_audio
            return combined_audio, True

        # Not note-taking mode, return initial recording
        return initial_audio, False

    def _handle_continuation_window(
        self,
        interaction_id: "uuid.UUID",
    ) -> tuple[str, str, "Intent"] | None:
        """Handle the 5-second continuation window after response playback.

        Listens for user speech within the continuation window. If detected,
        combines with original request and reprocesses.

        Args:
            interaction_id: Current interaction UUID

        Returns:
            Tuple of (combined_transcript, response_text, intent) if continuation
            detected, None otherwise
        """
        if not self._interrupt_manager or not self._capture or not self._transcriber:
            return None

        continuation_speech_event = threading.Event()
        continuation_audio: list[bytes] = []

        def on_window_expire() -> None:
            """Called when continuation window expires without speech."""
            logger.debug("Continuation window expired without speech")
            self._interrupt_manager.reset()

        # Start the continuation window
        self._interrupt_manager.start_continuation_window(on_expire=on_window_expire)
        logger.info("Continuation window started (5s)")

        # Monitor for speech within the window
        # Ensure capture is stopped and add delay to avoid PyAudio segfault
        if getattr(self._capture, 'is_active', False):
            self._capture.stop()
        time.sleep(0.1)  # Allow PyAudio to settle
        self._capture.start()
        try:
            window_start = time.time()
            while self._interrupt_manager._continuation_window.is_active:
                # Check timeout (should be handled by window, but safety check)
                if time.time() - window_start > 5.5:
                    break

                # Try to get audio chunk with short timeout
                try:
                    for chunk in self._capture.stream():
                        from .interrupt import calculate_energy

                        energy = calculate_energy(chunk.data)

                        if energy > 750:  # Same threshold as interrupt
                            # Speech detected - cancel window and process
                            self._interrupt_manager.cancel_continuation_window()
                            continuation_audio.append(chunk.data)
                            continuation_speech_event.set()
                            logger.info("Speech detected in continuation window")
                            break

                        # Short polling to allow window to expire
                        if not self._interrupt_manager._continuation_window.is_active:
                            break
                except Exception:
                    pass

                if continuation_speech_event.is_set():
                    break

                time.sleep(0.05)

        finally:
            self._capture.stop()

        # If speech was detected, record the rest and process
        if continuation_speech_event.is_set():
            # Record remaining speech with silence detection
            continuation_text = self._interrupt_manager.wait_for_interrupt_complete()

            if continuation_text:
                # Get combined request
                combined_request = self._interrupt_manager.get_combined_request()
                logger.info(f"Continuation combined: '{combined_request}'")
                _log_interaction_timing("captured", combined_request)

                # Re-classify and handle
                combined_intent = self._intent_classifier.classify(combined_request)
                logger.info(f"Continuation intent: {combined_intent.type.value}")

                combined_response = self._handle_intent(combined_intent, interaction_id)
                _log_interaction_timing("responded", combined_response)

                # Synthesize and play combined response
                if self._synthesizer and self._playback:
                    combined_synthesis = self._synthesizer.synthesize(combined_response)
                    self._playback.play(
                        combined_synthesis.audio, combined_synthesis.sample_rate
                    )

                return combined_request, combined_response, combined_intent

        return None

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
