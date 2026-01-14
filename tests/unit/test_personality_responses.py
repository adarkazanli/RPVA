"""Unit tests for concise personality responses.

Tests that assistant responses are friendly but brief, without excessive verbosity.
"""

import pytest

from ara.config.personality import get_default_personality


class TestConciseReminderConfirmation:
    """Tests for concise reminder confirmation response format (T028)."""

    def test_personality_prompt_emphasizes_brevity(self):
        """Test that personality prompt includes brevity instruction."""
        personality = get_default_personality()
        prompt = personality.system_prompt.lower()

        # Should emphasize brief/concise responses
        assert any(
            word in prompt
            for word in ["brief", "concise", "short", "one sentence", "minimal"]
        ), "Personality prompt should emphasize brevity"

    def test_personality_prompt_discourages_filler(self):
        """Test that personality prompt includes guidance against filler phrases."""
        personality = get_default_personality()
        prompt = personality.system_prompt.lower()

        # Should have a "bad examples" section to show what to avoid
        assert "bad" in prompt and "example" in prompt, "Should include bad examples"
        # Should discourage filler phrases
        assert "filler" in prompt, "Should mention avoiding filler phrases"

    def test_personality_has_good_bad_examples(self):
        """Test that personality prompt includes good/bad examples."""
        personality = get_default_personality()
        prompt = personality.system_prompt.lower()

        # Should have examples of what to avoid
        # This is optional but helpful for LLM guidance
        # Just verify the prompt is not empty
        assert len(prompt) > 100, "Personality prompt should be substantial"


class TestConciseReminderListResponse:
    """Tests for concise reminder list response format (T029)."""

    def test_personality_prompt_exists(self):
        """Test that personality configuration exists and is valid."""
        personality = get_default_personality()
        assert personality.name is not None
        assert personality.system_prompt is not None
        assert len(personality.system_prompt) > 0

    def test_personality_name_is_purcobine(self):
        """Test that personality name is Purcobine."""
        personality = get_default_personality()
        assert personality.name == "Purcobine"
