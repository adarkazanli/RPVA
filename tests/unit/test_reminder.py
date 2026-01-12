"""Unit tests for Reminder entity and ReminderManager."""

import uuid
from datetime import datetime, timedelta
from unittest import mock

import pytest

from ara.commands.reminder import (
    Reminder,
    ReminderManager,
    ReminderStatus,
    Recurrence,
    parse_reminder_time,
)


class TestReminderEntity:
    """Tests for Reminder dataclass."""

    def test_create_reminder(self) -> None:
        """Test creating a reminder with all fields."""
        remind_at = datetime.utcnow() + timedelta(hours=1)
        reminder = Reminder(
            id=uuid.uuid4(),
            message="call mom",
            remind_at=remind_at,
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
            created_at=datetime.utcnow(),
        )
        assert reminder.message == "call mom"
        assert reminder.recurrence == Recurrence.NONE
        assert reminder.status == ReminderStatus.PENDING
        assert reminder.triggered_at is None

    def test_reminder_with_recurrence(self) -> None:
        """Test creating a recurring reminder."""
        reminder = Reminder(
            id=uuid.uuid4(),
            message="take medication",
            remind_at=datetime.utcnow() + timedelta(hours=1),
            recurrence=Recurrence.DAILY,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
            created_at=datetime.utcnow(),
        )
        assert reminder.recurrence == Recurrence.DAILY

    def test_reminder_is_due(self) -> None:
        """Test checking if reminder is due."""
        past = datetime.utcnow() - timedelta(minutes=1)
        reminder = Reminder(
            id=uuid.uuid4(),
            message="test",
            remind_at=past,
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
            created_at=datetime.utcnow(),
        )
        assert reminder.is_due is True

    def test_reminder_not_due(self) -> None:
        """Test reminder is not due yet."""
        future = datetime.utcnow() + timedelta(hours=1)
        reminder = Reminder(
            id=uuid.uuid4(),
            message="test",
            remind_at=future,
            recurrence=Recurrence.NONE,
            status=ReminderStatus.PENDING,
            triggered_at=None,
            created_by_interaction=uuid.uuid4(),
            created_at=datetime.utcnow(),
        )
        assert reminder.is_due is False


class TestReminderStatus:
    """Tests for ReminderStatus enum."""

    def test_status_values(self) -> None:
        """Test all status values exist."""
        assert ReminderStatus.PENDING.value == "pending"
        assert ReminderStatus.TRIGGERED.value == "triggered"
        assert ReminderStatus.DISMISSED.value == "dismissed"
        assert ReminderStatus.CANCELLED.value == "cancelled"


class TestRecurrence:
    """Tests for Recurrence enum."""

    def test_recurrence_values(self) -> None:
        """Test all recurrence values exist."""
        assert Recurrence.NONE.value == "none"
        assert Recurrence.DAILY.value == "daily"
        assert Recurrence.WEEKLY.value == "weekly"
        assert Recurrence.MONTHLY.value == "monthly"


class TestReminderManager:
    """Tests for ReminderManager."""

    @pytest.fixture
    def manager(self) -> ReminderManager:
        """Create a ReminderManager instance."""
        return ReminderManager()

    def test_create_reminder(self, manager: ReminderManager) -> None:
        """Test creating a reminder through manager."""
        remind_at = datetime.utcnow() + timedelta(hours=1)
        interaction_id = uuid.uuid4()
        reminder = manager.create(
            message="call mom",
            remind_at=remind_at,
            interaction_id=interaction_id,
        )
        assert reminder.message == "call mom"
        assert reminder.status == ReminderStatus.PENDING
        assert reminder.created_by_interaction == interaction_id

    def test_create_recurring_reminder(self, manager: ReminderManager) -> None:
        """Test creating a recurring reminder."""
        reminder = manager.create(
            message="take medication",
            remind_at=datetime.utcnow() + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
            recurrence=Recurrence.DAILY,
        )
        assert reminder.recurrence == Recurrence.DAILY

    def test_cancel_reminder(self, manager: ReminderManager) -> None:
        """Test cancelling a reminder."""
        reminder = manager.create(
            message="test",
            remind_at=datetime.utcnow() + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )
        result = manager.cancel(reminder.id)
        assert result is True
        assert reminder.status == ReminderStatus.CANCELLED

    def test_cancel_nonexistent_reminder(self, manager: ReminderManager) -> None:
        """Test cancelling a reminder that doesn't exist."""
        result = manager.cancel(uuid.uuid4())
        assert result is False

    def test_get_reminder(self, manager: ReminderManager) -> None:
        """Test getting a reminder by ID."""
        reminder = manager.create(
            message="test",
            remind_at=datetime.utcnow() + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )
        retrieved = manager.get(reminder.id)
        assert retrieved is not None
        assert retrieved.id == reminder.id

    def test_get_nonexistent_reminder(self, manager: ReminderManager) -> None:
        """Test getting a reminder that doesn't exist."""
        result = manager.get(uuid.uuid4())
        assert result is None

    def test_list_pending_reminders(self, manager: ReminderManager) -> None:
        """Test listing pending reminders."""
        r1 = manager.create(
            message="r1",
            remind_at=datetime.utcnow() + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )
        r2 = manager.create(
            message="r2",
            remind_at=datetime.utcnow() + timedelta(hours=2),
            interaction_id=uuid.uuid4(),
        )
        manager.cancel(r1.id)

        pending = manager.list_pending()
        assert len(pending) == 1
        assert pending[0].id == r2.id

    def test_list_all_reminders(self, manager: ReminderManager) -> None:
        """Test listing all reminders."""
        manager.create(
            message="r1",
            remind_at=datetime.utcnow() + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )
        manager.create(
            message="r2",
            remind_at=datetime.utcnow() + timedelta(hours=2),
            interaction_id=uuid.uuid4(),
        )

        all_reminders = manager.list_all()
        assert len(all_reminders) == 2

    def test_check_due_reminders(self, manager: ReminderManager) -> None:
        """Test checking for due reminders."""
        # Create a reminder that is already due
        reminder = manager.create(
            message="test",
            remind_at=datetime.utcnow() - timedelta(minutes=1),
            interaction_id=uuid.uuid4(),
        )

        due = manager.check_due()
        assert len(due) == 1
        assert due[0].id == reminder.id

    def test_due_reminder_marked_triggered(self, manager: ReminderManager) -> None:
        """Test that due reminders are marked as triggered."""
        reminder = manager.create(
            message="test",
            remind_at=datetime.utcnow() - timedelta(minutes=1),
            interaction_id=uuid.uuid4(),
        )

        manager.check_due()
        assert reminder.status == ReminderStatus.TRIGGERED
        assert reminder.triggered_at is not None

    def test_dismiss_reminder(self, manager: ReminderManager) -> None:
        """Test dismissing a triggered reminder."""
        reminder = manager.create(
            message="test",
            remind_at=datetime.utcnow() - timedelta(minutes=1),
            interaction_id=uuid.uuid4(),
        )
        manager.check_due()

        result = manager.dismiss(reminder.id)
        assert result is True
        assert reminder.status == ReminderStatus.DISMISSED

    def test_recurring_reminder_creates_next(self, manager: ReminderManager) -> None:
        """Test that triggering a recurring reminder creates the next one."""
        reminder = manager.create(
            message="daily task",
            remind_at=datetime.utcnow() - timedelta(minutes=1),
            interaction_id=uuid.uuid4(),
            recurrence=Recurrence.DAILY,
        )

        manager.check_due()

        # Should now have 2 reminders - original triggered and new pending
        all_reminders = manager.list_all()
        assert len(all_reminders) == 2

        pending = manager.list_pending()
        assert len(pending) == 1
        assert pending[0].message == "daily task"
        # Next reminder should be ~24 hours later
        assert pending[0].remind_at > datetime.utcnow()


class TestParseReminderTime:
    """Tests for natural language time parsing for reminders."""

    def test_parse_relative_time(self) -> None:
        """Test parsing relative time expressions."""
        now = datetime.utcnow()

        result = parse_reminder_time("in 1 hour")
        assert result is not None
        assert result > now
        # Should be approximately 1 hour from now
        diff = (result - now).total_seconds()
        assert 3500 <= diff <= 3700

    def test_parse_relative_minutes(self) -> None:
        """Test parsing relative minutes."""
        now = datetime.utcnow()

        result = parse_reminder_time("in 30 minutes")
        assert result is not None
        diff = (result - now).total_seconds()
        assert 1700 <= diff <= 1900

    def test_parse_at_time(self) -> None:
        """Test parsing specific time."""
        result = parse_reminder_time("at 3:30 PM")
        assert result is not None
        assert result.hour == 15
        assert result.minute == 30

    def test_parse_at_time_24h(self) -> None:
        """Test parsing 24-hour time."""
        result = parse_reminder_time("at 14:00")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 0

    def test_parse_tomorrow(self) -> None:
        """Test parsing 'tomorrow' expressions."""
        now = datetime.utcnow()
        result = parse_reminder_time("tomorrow at 9 AM")
        assert result is not None
        assert result.day != now.day or result.month != now.month
        assert result.hour == 9

    def test_parse_invalid(self) -> None:
        """Test parsing invalid input returns None."""
        assert parse_reminder_time("invalid") is None
        assert parse_reminder_time("") is None
