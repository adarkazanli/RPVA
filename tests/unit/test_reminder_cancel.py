"""Unit tests for cancel by number functionality (T038, T039, T040)."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from ara.commands.reminder import ReminderManager
from ara.router.orchestrator import Orchestrator


class TestExtractReminderNumbers:
    """Tests for _extract_reminder_numbers helper."""

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

    def test_extract_single_cardinal_number(self, orchestrator: Orchestrator) -> None:
        """Test extracting a single cardinal number."""
        numbers = orchestrator._extract_reminder_numbers("cancel reminder 3")
        assert numbers == [3]

    def test_extract_reminder_number_n(self, orchestrator: Orchestrator) -> None:
        """Test extracting 'reminder number N' format."""
        numbers = orchestrator._extract_reminder_numbers("cancel reminder number 5")
        assert numbers == [5]

    def test_extract_ordinal_first(self, orchestrator: Orchestrator) -> None:
        """Test extracting ordinal 'first'."""
        numbers = orchestrator._extract_reminder_numbers("cancel the first reminder")
        assert numbers == [1]

    def test_extract_ordinal_second(self, orchestrator: Orchestrator) -> None:
        """Test extracting ordinal 'second'."""
        numbers = orchestrator._extract_reminder_numbers("cancel the second reminder")
        assert numbers == [2]

    def test_extract_ordinal_third(self, orchestrator: Orchestrator) -> None:
        """Test extracting ordinal 'third'."""
        numbers = orchestrator._extract_reminder_numbers("delete the third one")
        assert numbers == [3]

    def test_extract_all_ordinals_first_to_tenth(self, orchestrator: Orchestrator) -> None:
        """Test extracting ordinals first through tenth."""
        ordinal_texts = [
            ("first", 1),
            ("second", 2),
            ("third", 3),
            ("fourth", 4),
            ("fifth", 5),
            ("sixth", 6),
            ("seventh", 7),
            ("eighth", 8),
            ("ninth", 9),
            ("tenth", 10),
        ]

        for word, expected in ordinal_texts:
            numbers = orchestrator._extract_reminder_numbers(f"cancel the {word} reminder")
            assert expected in numbers, f"Failed for {word}"


class TestCancelBySingleNumber:
    """Tests for cancel by single number (T038)."""

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

    def test_cancel_single_number_valid(self, orchestrator: Orchestrator) -> None:
        """Test cancelling by a valid single number."""
        # Create 3 reminders
        for i in range(3):
            orchestrator.reminder_manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Cancel number 2
        orchestrator.process("cancel reminder number 2")

        # Verify second reminder was cancelled
        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 2
        messages = [r.message for r in pending]
        assert "reminder 1" not in messages  # index 1 (second) was cancelled

    def test_cancel_single_ordinal_valid(self, orchestrator: Orchestrator) -> None:
        """Test cancelling by ordinal word."""
        # Create 3 reminders
        for i in range(3):
            orchestrator.reminder_manager.create(
                message=f"task {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Cancel the first one
        orchestrator.process("cancel the first reminder")

        # Verify first reminder was cancelled
        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 2
        # First one (task 0) should be gone
        messages = [r.message for r in pending]
        assert "task 0" not in messages


class TestCancelByMultipleNumbers:
    """Tests for cancel by multiple numbers (T039)."""

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

    def test_extract_multiple_cardinal_numbers(self, orchestrator: Orchestrator) -> None:
        """Test extracting multiple cardinal numbers."""
        numbers = orchestrator._extract_reminder_numbers("cancel reminders 2, 4, and 5")
        assert sorted(numbers) == [2, 4, 5]

    def test_extract_multiple_ordinals(self, orchestrator: Orchestrator) -> None:
        """Test extracting multiple ordinal words."""
        numbers = orchestrator._extract_reminder_numbers("cancel the third and sixth reminders")
        assert sorted(numbers) == [3, 6]

    def test_extract_mixed_ordinals_and_cardinals(self, orchestrator: Orchestrator) -> None:
        """Test extracting mix of ordinals and cardinals."""
        numbers = orchestrator._extract_reminder_numbers("cancel the first and reminder 3")
        assert sorted(numbers) == [1, 3]

    def test_cancel_multiple_valid(self, orchestrator: Orchestrator) -> None:
        """Test cancelling multiple reminders at once."""
        # Create 5 reminders
        for i in range(5):
            orchestrator.reminder_manager.create(
                message=f"item {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Cancel 1, 3, 5 (first, third, fifth)
        orchestrator._extract_reminder_numbers("cancel the first, third, and fifth reminders")

        # Actually perform cancel via process
        orchestrator.process("cancel the first, third, and fifth reminders")

        # Verify correct ones cancelled (indices 0, 2, 4)
        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 2
        messages = [r.message for r in pending]
        assert "item 1" in messages  # second survived
        assert "item 3" in messages  # fourth survived


class TestInvalidNumberHandling:
    """Tests for invalid number handling (T040)."""

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

    def test_cancel_number_out_of_range(self, orchestrator: Orchestrator) -> None:
        """Test cancelling with number out of range."""
        # Create only 2 reminders
        for i in range(2):
            orchestrator.reminder_manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Try to cancel reminder 5
        response = orchestrator.process("cancel reminder 5")

        # Should get error message about having only N reminders
        assert "only have" in response.lower() or "2" in response

        # No reminders should have been cancelled
        pending = orchestrator.reminder_manager.list_pending()
        assert len(pending) == 2

    def test_cancel_zero_is_invalid(self, orchestrator: Orchestrator) -> None:
        """Test that cancelling reminder 0 is handled gracefully."""
        orchestrator.reminder_manager.create(
            message="test",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        numbers = orchestrator._extract_reminder_numbers("cancel reminder 0")
        # Zero should be filtered out (invalid)
        assert 0 not in numbers

    def test_cancel_negative_is_invalid(self, orchestrator: Orchestrator) -> None:
        """Test that negative numbers are filtered out."""
        numbers = orchestrator._extract_reminder_numbers("cancel reminder -1")
        # Negative numbers shouldn't be extracted
        assert -1 not in numbers

    def test_cancel_empty_list(self, orchestrator: Orchestrator) -> None:
        """Test cancelling when no reminders exist."""
        response = orchestrator.process("cancel reminder 1")

        # Should indicate no reminders
        assert "don't have" in response.lower() or "no" in response.lower()

    def test_cancel_with_some_invalid_numbers(self, orchestrator: Orchestrator) -> None:
        """Test cancelling with some valid and some invalid numbers."""
        # Create 3 reminders
        for i in range(3):
            orchestrator.reminder_manager.create(
                message=f"task {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        # Try to cancel 1 (valid) and 10 (invalid)
        response = orchestrator.process("cancel reminders 1 and 10")

        # Should report error about invalid number
        pending = orchestrator.reminder_manager.list_pending()
        # Behavior depends on implementation - either all fail or valid ones succeed
        # Check that we get informative response
        assert "only have" in response.lower() or len(pending) == 3
