"""Integration tests for reminder flow (T011, T019, T059)."""

import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
from ara.commands.reminder import ReminderManager
from ara.feedback.audio import MockFeedback
from ara.llm.mock import MockLanguageModel
from ara.router.orchestrator import Orchestrator
from ara.stt.mock import MockTranscriber
from ara.tts.mock import MockSynthesizer
from ara.wake_word.mock import MockWakeWordDetector


class TestReminderSetFlow:
    """Integration tests for reminder set flow (T011)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with reminder support and isolated state."""
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

        orch = Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )
        # Replace with isolated in-memory manager
        orch._reminder_manager = ReminderManager()
        return orch

    def test_set_reminder_via_process(self, orchestrator: Orchestrator) -> None:
        """Test setting a reminder through process method."""
        response = orchestrator.process("remind me to call mom in 1 hour")

        # Response should confirm the reminder
        assert "remind" in response.lower() or "got it" in response.lower()

        # Reminder should be created
        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) >= 1

    def test_set_reminder_response_includes_times(self, orchestrator: Orchestrator) -> None:
        """Test that set reminder response includes target time."""
        response = orchestrator.process("remind me to take medicine in 30 minutes")

        # Response should include time information
        assert ":" in response  # Time format includes colon
        # Should confirm the reminder was set (concise format from 003-timer-countdown)
        assert "reminder" in response.lower() or "got it" in response.lower()

    def test_set_reminder_flow_end_to_end(self, orchestrator: Orchestrator) -> None:
        """Test complete reminder set flow."""
        # Set reminder
        orchestrator.process("remind me in 2 hours to check email")

        # Query reminders
        query_response = orchestrator.process("what reminders do I have")

        # Should list the reminder
        assert "email" in query_response.lower() or "reminder" in query_response.lower()


class TestConcurrentReminderHandling:
    """Integration tests for concurrent reminder handling (T019)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with reminder support and isolated state."""
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

        orch = Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )
        # Replace with isolated in-memory manager
        orch._reminder_manager = ReminderManager()
        return orch

    def test_multiple_reminders_can_be_set(self, orchestrator: Orchestrator) -> None:
        """Test setting multiple reminders in sequence."""
        orchestrator.process("remind me in 1 hour to call mom")
        orchestrator.process("remind me in 2 hours to check email")
        orchestrator.process("remind me in 3 hours to take break")

        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 3

    def test_reminders_sorted_chronologically(self, orchestrator: Orchestrator) -> None:
        """Test that reminders are listed in chronological order."""
        # Create in non-chronological order
        orchestrator.process("remind me in 3 hours to task c")
        orchestrator.process("remind me in 1 hour to task a")
        orchestrator.process("remind me in 2 hours to task b")

        pending = orchestrator.reminder_manager.list_pending()

        # Should be sorted by time
        assert pending[0].remind_at < pending[1].remind_at < pending[2].remind_at

    def test_query_multiple_reminders(self, orchestrator: Orchestrator) -> None:
        """Test querying multiple reminders shows all."""
        # Create multiple reminders
        for i in range(3):
            orchestrator.reminder_manager.create(
                message=f"task {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        response = orchestrator.process("what reminders do I have")

        # Response should mention multiple
        assert "3" in response or "first" in response.lower()


class TestMissedReminderDelivery:
    """Integration tests for missed reminder delivery (T059)."""

    def test_missed_reminders_detected_on_startup(self) -> None:
        """Test that missed reminders are detected when manager starts."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # Create a manager and add a past reminder
        manager1 = ReminderManager(persistence_path=temp_path)
        manager1.create(
            message="missed task",
            remind_at=datetime.now(UTC) - timedelta(minutes=30),
            interaction_id=uuid.uuid4(),
        )

        # Create new manager (simulating restart)
        manager2 = ReminderManager(persistence_path=temp_path)
        missed = manager2.check_missed()

        assert len(missed) == 1
        assert missed[0].message == "missed task"

    def test_missed_reminders_with_multiple_past(self) -> None:
        """Test detection of multiple missed reminders."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        manager1 = ReminderManager(persistence_path=temp_path)

        # Create multiple past reminders
        for i in range(3):
            manager1.create(
                message=f"missed {i}",
                remind_at=datetime.now(UTC) - timedelta(minutes=10 * (i + 1)),
                interaction_id=uuid.uuid4(),
            )

        # Also add a future reminder
        manager1.create(
            message="future task",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        # Restart
        manager2 = ReminderManager(persistence_path=temp_path)
        missed = manager2.check_missed()

        # Should find 3 missed, not the future one
        assert len(missed) == 3

    def test_missed_reminders_not_double_counted(self) -> None:
        """Test that missed reminders aren't counted twice."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        manager = ReminderManager(persistence_path=temp_path)
        manager.create(
            message="missed task",
            remind_at=datetime.now(UTC) - timedelta(minutes=30),
            interaction_id=uuid.uuid4(),
        )

        # Check missed
        missed1 = manager.check_missed()
        assert len(missed1) == 1

        # Trigger the reminder via check_due
        manager.check_due()

        # Check missed again - should be empty now
        missed2 = manager.check_missed()
        assert len(missed2) == 0


class TestReminderFlowWithPersistence:
    """Integration tests for reminder flow with persistence."""

    def test_set_query_restart_query(self) -> None:
        """Test full flow: set, query, restart, query again."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        # First session
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()

        # Create orchestrator with persistence
        orch1 = Orchestrator(llm=mock_llm, feedback=mock_feedback)
        # Replace the default manager with one using temp path
        orch1._reminder_manager = ReminderManager(persistence_path=temp_path)

        # Set a reminder
        orch1.process("remind me in 1 hour to test persistence")

        # Verify it's there
        pending1 = orch1.reminder_manager.list_pending()
        assert len(pending1) == 1

        # "Restart" with new orchestrator
        orch2 = Orchestrator(llm=mock_llm, feedback=mock_feedback)
        orch2._reminder_manager = ReminderManager(persistence_path=temp_path)

        # Query - should still have the reminder
        pending2 = orch2.reminder_manager.list_pending()
        assert len(pending2) == 1
        assert "persistence" in pending2[0].message


class TestTenPlusConcurrentReminders:
    """Test for 10+ concurrent reminders without degradation (T022)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with reminder support and isolated state."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()

        orch = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )
        # Replace with isolated in-memory manager
        orch._reminder_manager = ReminderManager()
        return orch

    def test_ten_plus_reminders_created(self, orchestrator: Orchestrator) -> None:
        """Test creating 10+ reminders."""
        for i in range(15):
            orchestrator.reminder_manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 15

    def test_ten_plus_reminders_query_response(self, orchestrator: Orchestrator) -> None:
        """Test querying 10+ reminders produces valid response."""
        for i in range(12):
            orchestrator.reminder_manager.create(
                message=f"task {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        response = orchestrator.process("what reminders do I have")

        # Should mention the count
        assert "12" in response

        # Should use numeric ordinals for 11th and 12th
        assert "11th" in response or "eleventh" in response.lower()

    def test_ten_plus_reminders_persist_correctly(self) -> None:
        """Test that 10+ reminders persist and load correctly."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        manager1 = ReminderManager(persistence_path=temp_path)

        for i in range(15):
            manager1.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Reload
        manager2 = ReminderManager(persistence_path=temp_path)
        pending = manager2.list_pending()

        assert len(pending) == 15
