"""Unit tests for reminder persistence (T010, T018, T037, T058)."""

import json
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ara.commands.reminder import (
    Recurrence,
    ReminderManager,
    ReminderStatus,
)


class TestReminderCreationWithPersistence:
    """Tests for reminder creation with persistence (T010)."""

    @pytest.fixture
    def temp_path(self) -> Path:
        """Create a temporary file path for persistence."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            return Path(f.name)

    def test_create_reminder_saves_to_file(self, temp_path: Path) -> None:
        """Test that creating a reminder saves it to the persistence file."""
        manager = ReminderManager(persistence_path=temp_path)

        manager.create(
            message="test reminder",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        # Verify file was created and contains data
        assert temp_path.exists()
        with open(temp_path) as f:
            data = json.load(f)
        assert "reminders" in data
        assert len(data["reminders"]) == 1
        assert data["reminders"][0]["message"] == "test reminder"

    def test_load_reminder_on_init(self, temp_path: Path) -> None:
        """Test that reminders are loaded from file on initialization."""
        # Create a reminder with first manager
        manager1 = ReminderManager(persistence_path=temp_path)
        reminder = manager1.create(
            message="persistent reminder",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )
        reminder_id = reminder.id

        # Create new manager - should load existing reminder
        manager2 = ReminderManager(persistence_path=temp_path)
        loaded = manager2.get(reminder_id)

        assert loaded is not None
        assert loaded.message == "persistent reminder"
        assert loaded.id == reminder_id

    def test_persistence_preserves_reminder_fields(self, temp_path: Path) -> None:
        """Test that all reminder fields are preserved through persistence."""
        manager1 = ReminderManager(persistence_path=temp_path)
        remind_at = datetime.now(UTC) + timedelta(hours=2)
        interaction_id = uuid.uuid4()

        original = manager1.create(
            message="check all fields",
            remind_at=remind_at,
            interaction_id=interaction_id,
            recurrence=Recurrence.DAILY,
        )

        # Load in new manager
        manager2 = ReminderManager(persistence_path=temp_path)
        loaded = manager2.get(original.id)

        assert loaded is not None
        assert loaded.message == original.message
        assert loaded.recurrence == original.recurrence
        assert loaded.status == original.status
        assert loaded.created_by_interaction == original.created_by_interaction

    def test_in_memory_only_without_persistence_path(self) -> None:
        """Test that reminders work in memory-only mode."""
        manager = ReminderManager()  # No persistence path

        reminder = manager.create(
            message="memory only",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        assert manager.get(reminder.id) is not None
        assert len(manager.list_pending()) == 1


class TestMultipleReminderPersistence:
    """Tests for multiple reminder persistence (T018)."""

    @pytest.fixture
    def temp_path(self) -> Path:
        """Create a temporary file path for persistence."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            return Path(f.name)

    def test_save_multiple_reminders(self, temp_path: Path) -> None:
        """Test saving multiple reminders to persistence."""
        manager = ReminderManager(persistence_path=temp_path)

        # Create 5 reminders
        for i in range(5):
            manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Verify all saved
        with open(temp_path) as f:
            data = json.load(f)
        assert len(data["reminders"]) == 5

    def test_load_multiple_reminders(self, temp_path: Path) -> None:
        """Test loading multiple reminders from persistence."""
        manager1 = ReminderManager(persistence_path=temp_path)

        # Create multiple reminders
        ids = []
        for i in range(3):
            reminder = manager1.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )
            ids.append(reminder.id)

        # Load in new manager
        manager2 = ReminderManager(persistence_path=temp_path)

        # Verify all loaded
        for rid in ids:
            assert manager2.get(rid) is not None

        assert len(manager2.list_pending()) == 3

    def test_concurrent_reminders_preserve_order(self, temp_path: Path) -> None:
        """Test that reminder order is preserved through persistence."""
        manager1 = ReminderManager(persistence_path=temp_path)

        # Create reminders with different times
        times = [
            datetime.now(UTC) + timedelta(hours=3),
            datetime.now(UTC) + timedelta(hours=1),
            datetime.now(UTC) + timedelta(hours=2),
        ]

        for i, t in enumerate(times):
            manager1.create(
                message=f"reminder {i}",
                remind_at=t,
                interaction_id=uuid.uuid4(),
            )

        # Load and check sorted order
        manager2 = ReminderManager(persistence_path=temp_path)
        pending = manager2.list_pending()

        # Should be sorted by remind_at
        assert len(pending) == 3
        assert pending[0].remind_at <= pending[1].remind_at <= pending[2].remind_at


class TestCancelByDescriptionPersistence:
    """Tests for cancel by description with persistence (T037)."""

    @pytest.fixture
    def temp_path(self) -> Path:
        """Create a temporary file path for persistence."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            return Path(f.name)

    def test_cancel_persists_status_change(self, temp_path: Path) -> None:
        """Test that cancelling a reminder persists the status change."""
        manager1 = ReminderManager(persistence_path=temp_path)

        reminder = manager1.create(
            message="cancel me",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        # Cancel the reminder
        manager1.cancel(reminder.id)

        # Load in new manager
        manager2 = ReminderManager(persistence_path=temp_path)
        loaded = manager2.get(reminder.id)

        assert loaded is not None
        assert loaded.status == ReminderStatus.CANCELLED

    def test_cancelled_reminder_not_in_pending(self, temp_path: Path) -> None:
        """Test that cancelled reminders are not in pending list after reload."""
        manager1 = ReminderManager(persistence_path=temp_path)

        r1 = manager1.create(
            message="keep me",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )
        r2 = manager1.create(
            message="cancel me",
            remind_at=datetime.now(UTC) + timedelta(hours=2),
            interaction_id=uuid.uuid4(),
        )

        manager1.cancel(r2.id)

        # Load in new manager
        manager2 = ReminderManager(persistence_path=temp_path)
        pending = manager2.list_pending()

        assert len(pending) == 1
        assert pending[0].id == r1.id


class TestMissedReminderDetection:
    """Tests for missed reminder detection (T058)."""

    @pytest.fixture
    def temp_path(self) -> Path:
        """Create a temporary file path for persistence."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            return Path(f.name)

    def test_check_missed_finds_past_reminders(self, temp_path: Path) -> None:
        """Test that check_missed finds reminders with past remind_at times."""
        manager = ReminderManager(persistence_path=temp_path)

        # Create a reminder that's already past
        reminder = manager.create(
            message="missed reminder",
            remind_at=datetime.now(UTC) - timedelta(minutes=5),
            interaction_id=uuid.uuid4(),
        )

        missed = manager.check_missed()

        assert len(missed) == 1
        assert missed[0].id == reminder.id

    def test_check_missed_ignores_future_reminders(self, temp_path: Path) -> None:
        """Test that check_missed ignores future reminders."""
        manager = ReminderManager(persistence_path=temp_path)

        # Create a future reminder
        manager.create(
            message="future reminder",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        missed = manager.check_missed()

        assert len(missed) == 0

    def test_check_missed_ignores_triggered_reminders(self, temp_path: Path) -> None:
        """Test that check_missed ignores already triggered reminders."""
        manager = ReminderManager(persistence_path=temp_path)

        # Create a past reminder
        manager.create(
            message="triggered reminder",
            remind_at=datetime.now(UTC) - timedelta(minutes=5),
            interaction_id=uuid.uuid4(),
        )

        # Trigger it
        manager.check_due()

        # Should not be in missed anymore
        missed = manager.check_missed()
        assert len(missed) == 0

    def test_check_missed_returns_sorted_by_time(self, temp_path: Path) -> None:
        """Test that missed reminders are returned sorted by remind_at."""
        manager = ReminderManager(persistence_path=temp_path)

        # Create multiple past reminders
        manager.create(
            message="later missed",
            remind_at=datetime.now(UTC) - timedelta(minutes=1),
            interaction_id=uuid.uuid4(),
        )
        manager.create(
            message="earlier missed",
            remind_at=datetime.now(UTC) - timedelta(minutes=10),
            interaction_id=uuid.uuid4(),
        )
        manager.create(
            message="middle missed",
            remind_at=datetime.now(UTC) - timedelta(minutes=5),
            interaction_id=uuid.uuid4(),
        )

        missed = manager.check_missed()

        assert len(missed) == 3
        # Should be sorted by remind_at (earliest first)
        assert missed[0].remind_at <= missed[1].remind_at <= missed[2].remind_at

    def test_missed_reminders_persist_across_restart(self, temp_path: Path) -> None:
        """Test that missed reminders are found after manager restart."""
        # Create reminder with first manager
        manager1 = ReminderManager(persistence_path=temp_path)
        manager1.create(
            message="will be missed",
            remind_at=datetime.now(UTC) - timedelta(minutes=5),
            interaction_id=uuid.uuid4(),
        )

        # Simulate restart with new manager
        manager2 = ReminderManager(persistence_path=temp_path)
        missed = manager2.check_missed()

        assert len(missed) == 1
        assert missed[0].message == "will be missed"
