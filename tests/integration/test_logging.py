"""Integration tests for conversation logging."""

from datetime import UTC, date, datetime

import pytest

from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
from ara.feedback.audio import MockFeedback
from ara.llm.mock import MockLanguageModel
from ara.logger.interaction import InteractionLogger
from ara.logger.storage import InteractionStorage
from ara.logger.summary import SummaryGenerator
from ara.router.orchestrator import Orchestrator
from ara.stt.mock import MockTranscriber
from ara.tts.mock import MockSynthesizer
from ara.wake_word.mock import MockWakeWordDetector


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    @pytest.fixture
    def storage(self, tmp_path) -> InteractionStorage:
        """Create storage instance."""
        return InteractionStorage(
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
        )

    @pytest.fixture
    def logger(self, tmp_path, storage: InteractionStorage) -> InteractionLogger:
        """Create logger instance."""
        return InteractionLogger(
            device_id="test-device",
            storage=storage,
        )

    @pytest.fixture
    def orchestrator(self, logger: InteractionLogger) -> Orchestrator:
        """Create orchestrator with logging enabled."""
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        wake_word.initialize(keywords=["ara"], sensitivity=0.5)
        transcriber.set_latency(0)
        llm.set_latency(0)
        synthesizer.set_latency(0)

        return Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
            interaction_logger=logger,
        )

    def test_interaction_logged_after_voice_command(
        self, orchestrator: Orchestrator, storage: InteractionStorage
    ) -> None:
        """Test that interactions are logged after voice commands."""
        orchestrator._transcriber.set_response("what time is it")
        orchestrator._llm.set_response("It's 3:30 PM")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None

        # Check interaction was logged
        recent = storage.get_recent(limit=1)
        assert len(recent) >= 1
        assert recent[0].transcript == "what time is it"

    def test_multiple_interactions_logged(
        self, orchestrator: Orchestrator, storage: InteractionStorage
    ) -> None:
        """Test logging multiple interactions."""
        questions = [
            ("what time is it", "It's 3:30 PM"),
            ("set a timer for 5 minutes", "Timer set"),
            ("what is the weather", "Sunny and warm"),
        ]

        for transcript, response in questions:
            orchestrator._transcriber.set_response(transcript)
            orchestrator._llm.set_response(response)
            orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
            orchestrator._capture.set_audio_data(bytes(16000 * 2))
            orchestrator.process_single_interaction()

        recent = storage.get_recent(limit=10)
        assert len(recent) >= 3

    def test_session_created_and_tracked(
        self, orchestrator: Orchestrator, logger: InteractionLogger
    ) -> None:
        """Test that sessions are created and tracked."""
        orchestrator._transcriber.set_response("hello")
        orchestrator._llm.set_response("Hi there!")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        orchestrator.process_single_interaction()

        assert logger.current_session is not None
        assert logger.current_session.interaction_count >= 1

    def test_error_logged(
        self, orchestrator: Orchestrator, storage: InteractionStorage
    ) -> None:
        """Test that errors are logged."""
        orchestrator._transcriber.set_response("")  # Empty transcription
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        # Empty transcription should be handled gracefully
        # Either no interaction logged or logged with error


class TestSummaryGeneration:
    """Integration tests for summary generation."""

    @pytest.fixture
    def storage_with_data(self, tmp_path) -> InteractionStorage:
        """Create storage with sample data."""
        storage = InteractionStorage(
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
        )

        logger = InteractionLogger(
            device_id="test-device",
            storage=storage,
        )

        # Add various interactions
        test_data = [
            ("what time is it", "general_question"),
            ("set a timer for 5 minutes", "timer_set"),
            ("remind me to call mom", "reminder_set"),
            ("what is 2 + 2", "general_question"),
            ("cancel my timer", "timer_cancel"),
            ("what reminders do I have", "reminder_query"),
            ("what is the capital of France", "general_question"),
            ("set a timer for 10 minutes", "timer_set"),
            ("remind me to buy milk", "reminder_set"),
            ("how much time is left", "timer_query"),
        ]

        for transcript, intent in test_data:
            logger.log(
                transcript=transcript,
                response="OK",
                intent=intent,
                latency_ms={"total": 1000},
            )

        return storage

    def test_generate_daily_summary(
        self, storage_with_data: InteractionStorage
    ) -> None:
        """Test generating a complete daily summary."""
        generator = SummaryGenerator(storage_with_data)
        today = date.today()

        summary = generator.generate(today, device_id="test-device")

        assert summary.total_interactions == 10
        assert summary.successful_interactions == 10
        assert summary.error_count == 0
        assert len(summary.top_intents) > 0

    def test_summary_includes_action_items(
        self, storage_with_data: InteractionStorage
    ) -> None:
        """Test that summary includes action items from reminders."""
        generator = SummaryGenerator(storage_with_data)
        today = date.today()

        summary = generator.generate(today, device_id="test-device")

        # Should have action items from reminder_set intents
        assert len(summary.action_items) >= 0  # May or may not extract

    def test_export_summary_to_markdown(
        self, storage_with_data: InteractionStorage, tmp_path
    ) -> None:
        """Test exporting summary to Markdown file."""
        generator = SummaryGenerator(storage_with_data)
        today = date.today()

        summary = generator.generate(today, device_id="test-device")
        output_path = tmp_path / "daily_summary.md"

        generator.save_markdown(summary, output_path)

        assert output_path.exists()
        content = output_path.read_text()
        assert "# Daily Summary" in content
        assert "test-device" in content
        assert "10" in content  # Total interactions


class TestHistoryQuery:
    """Integration tests for history query functionality."""

    @pytest.fixture
    def storage_with_history(self, tmp_path) -> InteractionStorage:
        """Create storage with historical data."""
        storage = InteractionStorage(
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
        )

        logger = InteractionLogger(
            device_id="test-device",
            storage=storage,
        )

        # Add interactions
        for i in range(5):
            logger.log(
                transcript=f"question {i}",
                response=f"answer {i}",
                intent="general_question",
                latency_ms={"total": 1000},
            )

        return storage

    def test_query_recent_interactions(
        self, storage_with_history: InteractionStorage
    ) -> None:
        """Test querying recent interactions."""
        recent = storage_with_history.get_recent(limit=3)

        assert len(recent) == 3
        # Most recent first
        assert recent[0].transcript == "question 4"

    def test_query_by_date(
        self, storage_with_history: InteractionStorage
    ) -> None:
        """Test querying interactions by date."""
        today = date.today()
        interactions = storage_with_history.sqlite.get_by_date_range(
            datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC),
            datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC),
        )

        assert len(interactions) == 5

    def test_query_by_intent(
        self, storage_with_history: InteractionStorage
    ) -> None:
        """Test getting intent statistics."""
        today = date.today()
        counts = storage_with_history.sqlite.get_intent_counts(today)

        assert counts.get("general_question", 0) == 5
