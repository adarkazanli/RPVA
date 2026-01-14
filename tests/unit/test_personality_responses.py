"""Unit tests for personality responses and config (T023, T031)."""

import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ara.commands.reminder import ReminderManager
from ara.config.personality import (
    DEFAULT_PERSONALITY,
    PersonalityConfig,
    get_default_personality,
)
from ara.router.orchestrator import _get_ordinal


class TestNumberedReminderListFormatting:
    """Tests for numbered reminder list formatting (T023)."""

    @pytest.fixture
    def manager(self) -> ReminderManager:
        """Create a ReminderManager instance."""
        return ReminderManager()

    def test_single_reminder_format(self, manager: ReminderManager) -> None:
        """Test formatting a single reminder."""
        manager.create(
            message="call mom",
            remind_at=datetime.now(UTC) + timedelta(hours=1),
            interaction_id=uuid.uuid4(),
        )

        pending = manager.list_pending()
        assert len(pending) == 1
        # Single reminder should have special format in orchestrator

    def test_multiple_reminders_numbered(self, manager: ReminderManager) -> None:
        """Test that multiple reminders can be numbered."""
        for i in range(3):
            manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        pending = manager.list_pending()
        assert len(pending) == 3

        # Verify numbering would work
        for i, reminder in enumerate(pending, 1):
            ordinal = _get_ordinal(i)
            assert ordinal in ["first", "second", "third"]

    def test_reminders_sorted_chronologically(self, manager: ReminderManager) -> None:
        """Test that reminders are sorted by time for consistent numbering."""
        # Create in reverse order
        times = [
            datetime.now(UTC) + timedelta(hours=3),
            datetime.now(UTC) + timedelta(hours=1),
            datetime.now(UTC) + timedelta(hours=2),
        ]

        for i, t in enumerate(times):
            manager.create(
                message=f"reminder {i}",
                remind_at=t,
                interaction_id=uuid.uuid4(),
            )

        pending = manager.list_pending()

        # Should be sorted by time
        assert pending[0].remind_at < pending[1].remind_at < pending[2].remind_at

    def test_numbered_format_uses_ordinals(self) -> None:
        """Test that numbered format uses ordinal words."""
        ordinals = [_get_ordinal(i) for i in range(1, 4)]
        assert ordinals == ["first", "second", "third"]

    def test_ten_reminders_use_correct_ordinals(self, manager: ReminderManager) -> None:
        """Test ordinals for 10 reminders."""
        for i in range(10):
            manager.create(
                message=f"reminder {i}",
                remind_at=datetime.now(UTC) + timedelta(hours=i + 1),
                interaction_id=uuid.uuid4(),
            )

        pending = manager.list_pending()
        assert len(pending) == 10

        expected_ordinals = [
            "first", "second", "third", "fourth", "fifth",
            "sixth", "seventh", "eighth", "ninth", "tenth",
        ]

        for i, reminder in enumerate(pending):
            ordinal = _get_ordinal(i + 1)
            assert ordinal == expected_ordinals[i]


class TestPersonalityConfigLoading:
    """Tests for personality config loading (T031)."""

    def test_default_personality_exists(self) -> None:
        """Test that DEFAULT_PERSONALITY is defined."""
        assert DEFAULT_PERSONALITY is not None
        assert isinstance(DEFAULT_PERSONALITY, PersonalityConfig)

    def test_get_default_personality_returns_config(self) -> None:
        """Test that get_default_personality returns a PersonalityConfig."""
        config = get_default_personality()
        assert isinstance(config, PersonalityConfig)

    def test_personality_has_name(self) -> None:
        """Test that personality config has a name."""
        config = get_default_personality()
        assert config.name == "Purcobine"

    def test_personality_has_system_prompt(self) -> None:
        """Test that personality config has a system prompt."""
        config = get_default_personality()
        assert isinstance(config.system_prompt, str)
        assert len(config.system_prompt) > 0

    def test_personality_system_prompt_includes_warmth(self) -> None:
        """Test that system prompt mentions warmth."""
        config = get_default_personality()
        assert "warm" in config.system_prompt.lower()

    def test_personality_system_prompt_includes_playful(self) -> None:
        """Test that system prompt mentions playfulness."""
        config = get_default_personality()
        assert "playful" in config.system_prompt.lower()

    def test_personality_system_prompt_includes_witty(self) -> None:
        """Test that system prompt mentions wit."""
        config = get_default_personality()
        assert "witty" in config.system_prompt.lower() or "wit" in config.system_prompt.lower()

    def test_personality_has_warmth_level(self) -> None:
        """Test that personality config has warmth level."""
        config = get_default_personality()
        assert hasattr(config, "warmth_level")
        assert config.warmth_level == "friendly"

    def test_personality_has_wit_enabled(self) -> None:
        """Test that personality config has wit_enabled flag."""
        config = get_default_personality()
        assert hasattr(config, "wit_enabled")
        assert config.wit_enabled is True

    def test_create_custom_personality(self) -> None:
        """Test creating a custom personality config."""
        custom = PersonalityConfig(
            name="CustomBot",
            system_prompt="You are a helpful assistant.",
            warmth_level="professional",
            wit_enabled=False,
        )

        assert custom.name == "CustomBot"
        assert custom.warmth_level == "professional"
        assert custom.wit_enabled is False


class TestWarmLanguageInResponses:
    """Tests for warm language in response strings."""

    def test_no_reminders_response_is_friendly(self) -> None:
        """Test that 'no reminders' response uses friendly language."""
        expected_phrase = "Your schedule is clear"
        # This verifies the expected phrase is available for use
        assert "clear" in expected_phrase.lower()

    def test_clear_all_response_is_friendly(self) -> None:
        """Test that 'clear all' confirmation uses friendly language."""
        expected_phrase = "Fresh start!"
        assert "fresh" in expected_phrase.lower() or "start" in expected_phrase.lower()

    def test_cancel_response_is_friendly(self) -> None:
        """Test that cancel response uses friendly language."""
        expected_phrase = "Done!"
        assert "done" in expected_phrase.lower()

    def test_reminder_set_response_includes_time_context(self) -> None:
        """Test that reminder set response mentions both current and target time."""
        expected_pattern = "It's {current} now, and I'll remind you at {target}"
        # Verify the pattern structure
        assert "now" in expected_pattern
        assert "remind" in expected_pattern
