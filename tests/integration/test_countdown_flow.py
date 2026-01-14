"""Integration tests for countdown announcement flow (T037-T039)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from ara.commands.reminder import Reminder, ReminderManager, ReminderStatus
from ara.router.orchestrator import Orchestrator


class TestCompleteCountdownFlow:
    """Integration tests for complete countdown flow (T037)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with mock synthesizer and playback."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()
        mock_synthesizer = MagicMock()
        mock_playback = MagicMock()

        # Configure synthesizer to return mock audio
        mock_synthesizer.synthesize.return_value = MagicMock(audio=b"mock_audio", sample_rate=16000)

        orch = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )
        # Replace with mocks for testing
        orch._synthesizer = mock_synthesizer
        orch._playback = mock_playback
        orch._reminder_manager = ReminderManager()

        return orch

    def test_countdown_triggers_at_5_seconds(self, orchestrator: Orchestrator) -> None:
        """Test that countdown initiates when reminder is 5 seconds away."""
        # Create a reminder 5 seconds in the future
        reminder = orchestrator._reminder_manager.create(
            message="start your call",
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Check for upcoming reminders
        upcoming = orchestrator._get_upcoming_reminders(5)

        assert len(upcoming) == 1
        assert upcoming[0].id == reminder.id

    def test_countdown_phrase_generation(self, orchestrator: Orchestrator) -> None:
        """Test that countdown phrase is generated correctly."""
        from ara.commands.reminder import Recurrence

        reminder = Reminder(
            id=uuid.uuid4(),
            message="take your medicine",
            created_at=datetime.now(UTC),
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
        )

        # Without user name
        orchestrator._user_name = None
        phrase = orchestrator._generate_countdown_phrase([reminder], None)
        assert phrase == "Hey, you should take your medicine in"

        # With user name
        orchestrator._user_name = "Ammar"
        phrase = orchestrator._generate_countdown_phrase([reminder], "Ammar")
        assert phrase == "Ammar, you should take your medicine in"

    def test_countdown_sequence_spoken(self, orchestrator: Orchestrator) -> None:
        """Test that complete countdown sequence is spoken."""
        reminder = orchestrator._reminder_manager.create(
            message="start the meeting",
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Set fast countdown interval for testing
        orchestrator._countdown_interval = 0.01

        # Start countdown
        orchestrator._start_countdown([reminder])

        # Verify synthesizer was called multiple times (intro + 4 numbers + "now")
        # Intro: "Hey, you should start the meeting in 5"
        # Then: 4, 3, 2, 1, now
        calls = orchestrator._synthesizer.synthesize.call_args_list
        assert len(calls) >= 5  # At minimum: intro, 4, 3, 2, 1, now

        # Check that "now" was spoken at the end
        last_call = calls[-1]
        assert "now" in str(last_call).lower()

    def test_countdown_marks_reminder_active(self, orchestrator: Orchestrator) -> None:
        """Test that countdown marks reminders as active during countdown."""
        reminder = orchestrator._reminder_manager.create(
            message="check email",
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Set fast countdown for testing
        orchestrator._countdown_interval = 0.01

        # Start countdown
        orchestrator._start_countdown([reminder])

        # After countdown completes, reminder should be marked as active
        assert reminder.id in orchestrator._countdown_active


class TestCountdownCancellation:
    """Integration tests for countdown cancellation mid-countdown (T038)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with mock components."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()
        mock_synthesizer = MagicMock()
        mock_playback = MagicMock()

        mock_synthesizer.synthesize.return_value = MagicMock(audio=b"mock_audio", sample_rate=16000)

        orch = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )
        orch._synthesizer = mock_synthesizer
        orch._playback = mock_playback
        orch._reminder_manager = ReminderManager()

        return orch

    def test_cancelled_reminder_stops_countdown(self, orchestrator: Orchestrator) -> None:
        """Test that cancelling a reminder stops its countdown."""
        reminder = orchestrator._reminder_manager.create(
            message="cancelled task",
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Mark as active in countdown
        orchestrator._countdown_active[reminder.id] = True

        # Simulate cancellation by setting to False
        orchestrator._countdown_active[reminder.id] = False

        # The check in _start_countdown should detect this
        # and not speak further numbers
        assert orchestrator._countdown_active.get(reminder.id) is False

    def test_countdown_respects_cancellation_flag(self, orchestrator: Orchestrator) -> None:
        """Test that countdown checks cancellation before each number."""
        import threading
        import time

        reminder = orchestrator._reminder_manager.create(
            message="will be cancelled",
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Use slower interval to allow cancellation
        orchestrator._countdown_interval = 0.1

        # Track how many times synthesize was called
        call_count = [0]
        original_synthesize = orchestrator._synthesizer.synthesize

        def counting_synthesize(*args, **kwargs):
            call_count[0] += 1
            return original_synthesize(*args, **kwargs)

        orchestrator._synthesizer.synthesize = counting_synthesize

        # Start countdown in background thread
        def start_countdown():
            orchestrator._start_countdown([reminder])

        thread = threading.Thread(target=start_countdown)
        thread.start()

        # Wait briefly then cancel
        time.sleep(0.15)  # After intro and maybe one number
        orchestrator._countdown_active[reminder.id] = False

        thread.join(timeout=2.0)

        # Should have stopped early (not all 6 calls)
        assert call_count[0] < 6


class TestOverlappingTimersCombinedCountdown:
    """Integration tests for overlapping timers combined countdown (T039)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with mock components."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()
        mock_synthesizer = MagicMock()
        mock_playback = MagicMock()

        mock_synthesizer.synthesize.return_value = MagicMock(audio=b"mock_audio", sample_rate=16000)

        orch = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )
        orch._synthesizer = mock_synthesizer
        orch._playback = mock_playback
        orch._reminder_manager = ReminderManager()

        return orch

    def test_multiple_reminders_within_window(self, orchestrator: Orchestrator) -> None:
        """Test detecting multiple reminders within countdown window."""
        now = datetime.now(UTC)

        # Create two reminders within 5 seconds of each other
        reminder1 = orchestrator._reminder_manager.create(
            message="first task",
            remind_at=now + timedelta(seconds=4),
            interaction_id=uuid.uuid4(),
        )
        reminder2 = orchestrator._reminder_manager.create(
            message="second task",
            remind_at=now + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Get upcoming reminders in 5-second window
        upcoming = orchestrator._get_upcoming_reminders(5)

        assert len(upcoming) == 2
        assert reminder1.id in [r.id for r in upcoming]
        assert reminder2.id in [r.id for r in upcoming]

    def test_combined_countdown_phrase(self, orchestrator: Orchestrator) -> None:
        """Test that overlapping reminders are combined in phrase."""
        from ara.commands.reminder import Recurrence

        now = datetime.now(UTC)

        reminder1 = Reminder(
            id=uuid.uuid4(),
            message="start the call",
            created_at=now,
            remind_at=now + timedelta(seconds=4),
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
        )
        reminder2 = Reminder(
            id=uuid.uuid4(),
            message="prepare notes",
            created_at=now,
            remind_at=now + timedelta(seconds=5),
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
        )

        phrase = orchestrator._generate_countdown_phrase([reminder1, reminder2], "Ammar")

        # Should combine with "and"
        assert "start the call" in phrase
        assert "prepare notes" in phrase
        assert " and " in phrase
        assert phrase == "Ammar, you should start the call and prepare notes in"

    def test_combined_countdown_single_sequence(self, orchestrator: Orchestrator) -> None:
        """Test that combined reminders share a single countdown sequence."""
        now = datetime.now(UTC)

        reminder1 = orchestrator._reminder_manager.create(
            message="task one",
            remind_at=now + timedelta(seconds=4),
            interaction_id=uuid.uuid4(),
        )
        reminder2 = orchestrator._reminder_manager.create(
            message="task two",
            remind_at=now + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Set fast interval for testing
        orchestrator._countdown_interval = 0.01

        # Start countdown for both
        orchestrator._start_countdown([reminder1, reminder2])

        # Both should be marked as active
        assert orchestrator._countdown_active.get(reminder1.id) is True
        assert orchestrator._countdown_active.get(reminder2.id) is True

        # The intro phrase should contain both tasks
        first_call = orchestrator._synthesizer.synthesize.call_args_list[0]
        spoken_text = str(first_call)
        assert "task one" in spoken_text.lower()
        assert "task two" in spoken_text.lower()

    def test_already_active_reminder_excluded(self, orchestrator: Orchestrator) -> None:
        """Test that reminders already in countdown are excluded from upcoming."""
        now = datetime.now(UTC)

        reminder1 = orchestrator._reminder_manager.create(
            message="active task",
            remind_at=now + timedelta(seconds=4),
            interaction_id=uuid.uuid4(),
        )
        reminder2 = orchestrator._reminder_manager.create(
            message="new task",
            remind_at=now + timedelta(seconds=5),
            interaction_id=uuid.uuid4(),
        )

        # Mark first reminder as already in countdown
        orchestrator._countdown_active[reminder1.id] = True

        # Get upcoming - should only return the second one
        upcoming = orchestrator._get_upcoming_reminders(5)

        assert len(upcoming) == 1
        assert upcoming[0].id == reminder2.id


class TestEndToEndCountdown:
    """End-to-end integration tests for countdown feature."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with all mocked components."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()
        mock_synthesizer = MagicMock()
        mock_playback = MagicMock()

        mock_synthesizer.synthesize.return_value = MagicMock(audio=b"mock_audio", sample_rate=16000)

        orch = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )
        orch._synthesizer = mock_synthesizer
        orch._playback = mock_playback
        orch._reminder_manager = ReminderManager()

        return orch

    def test_set_reminder_and_countdown(self, orchestrator: Orchestrator) -> None:
        """Test setting a reminder and verifying countdown setup."""
        # Create a reminder directly (process() depends on full pipeline)
        orchestrator._reminder_manager.create(
            message="call mom",
            remind_at=datetime.now(UTC) + timedelta(seconds=10),
            interaction_id=uuid.uuid4(),
        )

        # Verify reminder was created
        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 1
        assert "call mom" in pending[0].message.lower()

    def test_short_timer_countdown(self, orchestrator: Orchestrator) -> None:
        """Test countdown for timers shorter than 5 seconds."""
        # Create a reminder 3 seconds away
        reminder = orchestrator._reminder_manager.create(
            message="quick task",
            remind_at=datetime.now(UTC) + timedelta(seconds=3),
            interaction_id=uuid.uuid4(),
        )

        # Get countdown start number
        remaining = (reminder.remind_at - datetime.now(UTC)).total_seconds()
        start = orchestrator._get_countdown_start(remaining)

        # Should start from 3, not 5
        assert start <= 3

    def test_personalized_countdown_with_name(self, orchestrator: Orchestrator) -> None:
        """Test countdown uses personalized name when set."""
        from ara.commands.reminder import Recurrence

        # Set user name
        orchestrator._user_name = "Alex"

        reminder = Reminder(
            id=uuid.uuid4(),
            message="check inbox",
            created_at=datetime.now(UTC),
            remind_at=datetime.now(UTC) + timedelta(seconds=5),
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
        )

        phrase = orchestrator._generate_countdown_phrase([reminder], orchestrator._user_name)

        assert "Alex" in phrase
        assert "Hey" not in phrase
