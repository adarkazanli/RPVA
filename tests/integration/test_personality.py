"""Integration tests for personality system prompt application (T032)."""

from unittest.mock import MagicMock

import pytest

from ara.config.personality import get_default_personality
from ara.router.orchestrator import Orchestrator


class TestSystemPromptApplication:
    """Integration tests for system prompt application (T032)."""

    def test_orchestrator_sets_system_prompt_on_init(self) -> None:
        """Test that orchestrator sets system prompt when LLM is provided."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()

        Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )

        # Verify set_system_prompt was called
        mock_llm.set_system_prompt.assert_called_once()

        # Get the prompt that was set
        call_args = mock_llm.set_system_prompt.call_args
        prompt = call_args[0][0]

        # Verify it's the Purcobine prompt
        assert "warm" in prompt.lower() or "purcobine" in prompt.lower()

    def test_system_prompt_contains_personality_traits(self) -> None:
        """Test that system prompt contains key personality traits."""
        personality = get_default_personality()

        assert "warm" in personality.system_prompt.lower()
        # Updated for concise tone (003-timer-countdown): now emphasizes brief/clear over playful/witty
        assert (
            "brief" in personality.system_prompt.lower()
            or "concise" in personality.system_prompt.lower()
        )
        assert (
            "clear" in personality.system_prompt.lower()
            or "direct" in personality.system_prompt.lower()
        )

    def test_system_prompt_contains_voice_assistant_guidance(self) -> None:
        """Test that system prompt includes voice assistant context."""
        personality = get_default_personality()

        # Should mention being a voice assistant and keeping responses concise
        assert "voice" in personality.system_prompt.lower()
        assert (
            "concise" in personality.system_prompt.lower()
            or "short" in personality.system_prompt.lower()
        )

    def test_orchestrator_loads_personality_name(self) -> None:
        """Test that orchestrator loads the personality name."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="OK")
        mock_feedback = MagicMock()

        orchestrator = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )

        assert orchestrator._personality.name == "Purcobine"

    def test_llm_receives_system_prompt_for_general_questions(self) -> None:
        """Test that LLM uses system prompt for general questions."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Paris is the capital of France."
        mock_llm.generate.return_value = mock_response
        mock_feedback = MagicMock()

        orchestrator = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )

        # Process a general question
        orchestrator.process("What is the capital of France?")

        # LLM should have been called
        assert mock_llm.generate.called

    def test_no_error_when_llm_not_provided(self) -> None:
        """Test that orchestrator doesn't error when LLM is None."""
        mock_feedback = MagicMock()

        # Should not raise an error
        orchestrator = Orchestrator(
            llm=None,
            feedback=mock_feedback,
        )

        # Personality should still be loaded
        assert orchestrator._personality is not None


class TestPersonalityInResponses:
    """Tests for personality in orchestrator responses."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with mock LLM and isolated state."""
        mock_llm = MagicMock()
        mock_llm.generate.return_value = MagicMock(text="Sure, I can help with that!")
        mock_feedback = MagicMock()

        from ara.commands.reminder import ReminderManager

        orch = Orchestrator(
            llm=mock_llm,
            feedback=mock_feedback,
        )
        # Replace with isolated in-memory manager
        orch._reminder_manager = ReminderManager()
        return orch

    def test_reminder_responses_are_warm(self, orchestrator: Orchestrator) -> None:
        """Test that reminder responses use warm language."""
        response = orchestrator.process("remind me in 1 hour to check email")

        # Should use friendly confirmation
        assert "got it" in response.lower() or "i'll remind" in response.lower()

    def test_no_reminders_response_is_friendly(self, orchestrator: Orchestrator) -> None:
        """Test that 'no reminders' message is friendly."""
        response = orchestrator.process("what reminders do I have")

        # Should be warm, not robotic
        assert "clear" in response.lower() or "no reminders" in response.lower()

    def test_clear_all_response_is_encouraging(self, orchestrator: Orchestrator) -> None:
        """Test that clear all response is encouraging."""
        # First create some reminders
        orchestrator.process("remind me in 1 hour to task 1")
        orchestrator.process("remind me in 2 hours to task 2")

        response = orchestrator.process("clear all reminders")

        # Should be positive
        assert "done" in response.lower() or "cleared" in response.lower()


class TestPersonalityConfigStructure:
    """Tests for personality config structure."""

    def test_personality_config_has_all_required_fields(self) -> None:
        """Test that PersonalityConfig has all required fields."""
        personality = get_default_personality()

        assert hasattr(personality, "name")
        assert hasattr(personality, "system_prompt")
        assert hasattr(personality, "warmth_level")
        assert hasattr(personality, "wit_enabled")

    def test_personality_config_fields_have_correct_types(self) -> None:
        """Test that PersonalityConfig fields have correct types."""
        personality = get_default_personality()

        assert isinstance(personality.name, str)
        assert isinstance(personality.system_prompt, str)
        assert isinstance(personality.warmth_level, str)
        assert isinstance(personality.wit_enabled, bool)

    def test_default_personality_values(self) -> None:
        """Test default personality configuration values."""
        personality = get_default_personality()

        assert personality.name == "Purcobine"
        assert personality.warmth_level == "caring"
        # Updated for warm/witty tone: wit_enabled is True
        assert personality.wit_enabled is True
        assert len(personality.system_prompt) > 100  # Should be substantial
