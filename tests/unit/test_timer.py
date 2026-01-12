"""Unit tests for Timer entity and TimerManager."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ara.commands.timer import (
    Timer,
    TimerManager,
    TimerStatus,
    parse_duration,
)


class TestTimerEntity:
    """Tests for Timer dataclass."""

    def test_create_timer(self) -> None:
        """Test creating a timer with all fields."""
        timer = Timer(
            id=uuid.uuid4(),
            name="pasta timer",
            duration_seconds=300,
            started_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=300),
            status=TimerStatus.RUNNING,
            alert_played=False,
            created_by_interaction=uuid.uuid4(),
        )
        assert timer.name == "pasta timer"
        assert timer.duration_seconds == 300
        assert timer.status == TimerStatus.RUNNING
        assert timer.alert_played is False

    def test_timer_without_name(self) -> None:
        """Test creating a timer without a name."""
        timer = Timer(
            id=uuid.uuid4(),
            name=None,
            duration_seconds=60,
            started_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(seconds=60),
            status=TimerStatus.RUNNING,
            alert_played=False,
            created_by_interaction=uuid.uuid4(),
        )
        assert timer.name is None

    def test_timer_remaining_seconds(self) -> None:
        """Test calculating remaining seconds."""
        now = datetime.now(UTC)
        timer = Timer(
            id=uuid.uuid4(),
            name=None,
            duration_seconds=300,
            started_at=now,
            expires_at=now + timedelta(seconds=300),
            status=TimerStatus.RUNNING,
            alert_played=False,
            created_by_interaction=uuid.uuid4(),
        )
        remaining = timer.remaining_seconds
        assert 299 <= remaining <= 300

    def test_timer_is_expired(self) -> None:
        """Test checking if timer is expired."""
        past = datetime.now(UTC) - timedelta(seconds=10)
        timer = Timer(
            id=uuid.uuid4(),
            name=None,
            duration_seconds=5,
            started_at=past - timedelta(seconds=5),
            expires_at=past,
            status=TimerStatus.RUNNING,
            alert_played=False,
            created_by_interaction=uuid.uuid4(),
        )
        assert timer.is_expired is True


class TestTimerStatus:
    """Tests for TimerStatus enum."""

    def test_status_values(self) -> None:
        """Test all status values exist."""
        assert TimerStatus.RUNNING.value == "running"
        assert TimerStatus.PAUSED.value == "paused"
        assert TimerStatus.COMPLETED.value == "completed"
        assert TimerStatus.CANCELLED.value == "cancelled"


class TestTimerManager:
    """Tests for TimerManager."""

    @pytest.fixture
    def manager(self) -> TimerManager:
        """Create a TimerManager instance."""
        return TimerManager()

    def test_create_timer(self, manager: TimerManager) -> None:
        """Test creating a timer through manager."""
        interaction_id = uuid.uuid4()
        timer = manager.create(
            duration_seconds=300,
            name="test timer",
            interaction_id=interaction_id,
        )
        assert timer.name == "test timer"
        assert timer.duration_seconds == 300
        assert timer.status == TimerStatus.RUNNING
        assert timer.created_by_interaction == interaction_id

    def test_create_timer_without_name(self, manager: TimerManager) -> None:
        """Test creating a timer without a name."""
        timer = manager.create(
            duration_seconds=60,
            interaction_id=uuid.uuid4(),
        )
        assert timer.name is None
        assert timer.duration_seconds == 60

    def test_cancel_timer(self, manager: TimerManager) -> None:
        """Test cancelling a timer."""
        timer = manager.create(
            duration_seconds=300,
            interaction_id=uuid.uuid4(),
        )
        result = manager.cancel(timer.id)
        assert result is True
        assert timer.status == TimerStatus.CANCELLED

    def test_cancel_nonexistent_timer(self, manager: TimerManager) -> None:
        """Test cancelling a timer that doesn't exist."""
        result = manager.cancel(uuid.uuid4())
        assert result is False

    def test_get_timer(self, manager: TimerManager) -> None:
        """Test getting a timer by ID."""
        timer = manager.create(
            duration_seconds=300,
            interaction_id=uuid.uuid4(),
        )
        retrieved = manager.get(timer.id)
        assert retrieved is not None
        assert retrieved.id == timer.id

    def test_get_nonexistent_timer(self, manager: TimerManager) -> None:
        """Test getting a timer that doesn't exist."""
        result = manager.get(uuid.uuid4())
        assert result is None

    def test_list_active_timers(self, manager: TimerManager) -> None:
        """Test listing active timers."""
        timer1 = manager.create(duration_seconds=300, interaction_id=uuid.uuid4())
        timer2 = manager.create(duration_seconds=600, interaction_id=uuid.uuid4())
        manager.cancel(timer1.id)

        active = manager.list_active()
        assert len(active) == 1
        assert active[0].id == timer2.id

    def test_list_all_timers(self, manager: TimerManager) -> None:
        """Test listing all timers."""
        manager.create(duration_seconds=300, interaction_id=uuid.uuid4())
        manager.create(duration_seconds=600, interaction_id=uuid.uuid4())

        all_timers = manager.list_all()
        assert len(all_timers) == 2

    def test_check_expired_timers(self, manager: TimerManager) -> None:
        """Test checking for expired timers."""
        # Create a timer that expires immediately
        timer = manager.create(
            duration_seconds=0,
            interaction_id=uuid.uuid4(),
        )
        # Force expiration time to past
        timer.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        expired = manager.check_expired()
        assert len(expired) == 1
        assert expired[0].id == timer.id

    def test_expired_timer_marked_completed(self, manager: TimerManager) -> None:
        """Test that expired timers are marked as completed."""
        timer = manager.create(
            duration_seconds=0,
            interaction_id=uuid.uuid4(),
        )
        timer.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        manager.check_expired()
        assert timer.status == TimerStatus.COMPLETED
        assert timer.alert_played is True

    def test_pause_timer(self, manager: TimerManager) -> None:
        """Test pausing a timer."""
        timer = manager.create(
            duration_seconds=300,
            interaction_id=uuid.uuid4(),
        )
        result = manager.pause(timer.id)
        assert result is True
        assert timer.status == TimerStatus.PAUSED

    def test_resume_timer(self, manager: TimerManager) -> None:
        """Test resuming a paused timer."""
        timer = manager.create(
            duration_seconds=300,
            interaction_id=uuid.uuid4(),
        )
        manager.pause(timer.id)
        result = manager.resume(timer.id)
        assert result is True
        assert timer.status == TimerStatus.RUNNING


class TestParseDuration:
    """Tests for natural language duration parsing."""

    def test_parse_seconds(self) -> None:
        """Test parsing seconds."""
        assert parse_duration("30 seconds") == 30
        assert parse_duration("1 second") == 1
        assert parse_duration("45 secs") == 45

    def test_parse_minutes(self) -> None:
        """Test parsing minutes."""
        assert parse_duration("5 minutes") == 300
        assert parse_duration("1 minute") == 60
        assert parse_duration("10 mins") == 600

    def test_parse_hours(self) -> None:
        """Test parsing hours."""
        assert parse_duration("1 hour") == 3600
        assert parse_duration("2 hours") == 7200

    def test_parse_combined(self) -> None:
        """Test parsing combined durations."""
        assert parse_duration("1 hour and 30 minutes") == 5400
        assert parse_duration("2 minutes and 30 seconds") == 150

    def test_parse_numeric_only(self) -> None:
        """Test parsing numeric-only input (assumes minutes)."""
        assert parse_duration("5") == 300  # 5 minutes

    def test_parse_invalid(self) -> None:
        """Test parsing invalid input returns None."""
        assert parse_duration("invalid") is None
        assert parse_duration("") is None

    def test_parse_case_insensitive(self) -> None:
        """Test parsing is case insensitive."""
        assert parse_duration("5 MINUTES") == 300
        assert parse_duration("1 Hour") == 3600
