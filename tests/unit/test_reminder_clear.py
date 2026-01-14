"""Unit tests for clear all reminders functionality (T050, T051)."""

import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ara.commands.reminder import ReminderManager, ReminderStatus
from ara.router.intent import IntentClassifier, IntentType
from ara.router.orchestrator import Orchestrator


class TestClearAllWithCountConfirmation:
    """Tests for clear all with count confirmation (T050)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create a minimal orchestrator for testing with isolated state."""
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

    def test_clear_all_returns_count(self) -> None:
        """Test that clear_all returns the count of cleared reminders."""
        manager = ReminderManager()

        # Create 5 reminders
        for i in range(5):
            manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        count = manager.clear_all()
        assert count == 5

    def test_clear_all_removes_all_pending(self) -> None:
        """Test that clear_all removes all pending reminders."""
        manager = ReminderManager()

        # Create reminders
        for i in range(3):
            manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        manager.clear_all()

        pending = manager.list_pending()
        assert len(pending) == 0

    def test_clear_all_response_includes_count(self, orchestrator: Orchestrator) -> None:
        """Test that clear all response mentions the count."""
        # Create 3 reminders
        for i in range(3):
            orchestrator.reminder_manager.create(
                message=f"task {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        response = orchestrator.process("clear all my reminders")

        # Response should mention the count
        assert "3" in response

    def test_clear_all_sets_cancelled_status(self) -> None:
        """Test that clear_all sets status to CANCELLED."""
        manager = ReminderManager()

        reminders = []
        for i in range(3):
            r = manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )
            reminders.append(r)

        manager.clear_all()

        # All should be cancelled
        for r in reminders:
            assert r.status == ReminderStatus.CANCELLED

    def test_clear_all_persists(self) -> None:
        """Test that clear_all persists the changes."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = Path(f.name)

        manager1 = ReminderManager(persistence_path=temp_path)

        # Create and clear
        for i in range(3):
            manager1.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )
        manager1.clear_all()

        # Load in new manager
        manager2 = ReminderManager(persistence_path=temp_path)
        pending = manager2.list_pending()

        assert len(pending) == 0


class TestClearAllWhenEmpty:
    """Tests for clear all when empty (T051)."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create a minimal orchestrator for testing with isolated state."""
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

    def test_clear_all_empty_returns_zero(self) -> None:
        """Test that clear_all returns 0 when no reminders exist."""
        manager = ReminderManager()
        count = manager.clear_all()
        assert count == 0

    def test_clear_all_empty_response(self, orchestrator: Orchestrator) -> None:
        """Test response when clearing empty reminder list."""
        response = orchestrator.process("clear all reminders")

        # Should indicate no reminders to clear
        assert "don't have" in response.lower() or "empty" in response.lower() or "no" in response.lower()

    def test_clear_all_does_not_affect_non_pending(self) -> None:
        """Test that clear_all only affects pending reminders."""
        manager = ReminderManager()

        # Create a reminder and trigger it
        manager.create(
            message="triggered reminder",
            remind_at=datetime.now(UTC) - timedelta(minutes=1),
            interaction_id=uuid.uuid4(),
        )
        manager.check_due()  # Triggers the reminder

        # Now clear_all - should return 0 since the triggered one isn't pending
        count = manager.clear_all()
        assert count == 0

        # The triggered reminder should still exist
        all_reminders = manager.list_all()
        assert len(all_reminders) == 1
        assert all_reminders[0].status == ReminderStatus.TRIGGERED


class TestClearAllIntent:
    """Tests for clear all intent classification."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create an IntentClassifier instance."""
        return IntentClassifier()

    def test_classify_clear_all_reminders(self, classifier: IntentClassifier) -> None:
        """Test classifying 'clear all reminders'."""
        intent = classifier.classify("clear all reminders")
        assert intent.type == IntentType.REMINDER_CLEAR_ALL

    def test_classify_delete_all_reminders(self, classifier: IntentClassifier) -> None:
        """Test classifying 'delete all reminders'."""
        intent = classifier.classify("delete all my reminders")
        assert intent.type == IntentType.REMINDER_CLEAR_ALL

    def test_classify_remove_all_reminders(self, classifier: IntentClassifier) -> None:
        """Test classifying 'remove all reminders'."""
        intent = classifier.classify("remove all reminders")
        assert intent.type == IntentType.REMINDER_CLEAR_ALL

    def test_classify_cancel_all_reminders(self, classifier: IntentClassifier) -> None:
        """Test classifying 'cancel all reminders'."""
        intent = classifier.classify("cancel all my reminders")
        assert intent.type == IntentType.REMINDER_CLEAR_ALL

    def test_clear_all_has_high_confidence(self, classifier: IntentClassifier) -> None:
        """Test that clear all intent has high confidence."""
        intent = classifier.classify("clear all reminders")
        assert intent.confidence >= 0.9
