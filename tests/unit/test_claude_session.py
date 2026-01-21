"""Unit tests for ClaudeSession.

Tests the session management for Claude conversations including
message history and follow-up window timing.
"""

import time
from datetime import UTC, datetime

from ara.claude.session import ClaudeSession


class TestClaudeSessionMessageManagement:
    """Tests for ClaudeSession message management (T026)."""

    def test_add_user_message_stores_content(self) -> None:
        """Test that add_user_message stores the message content."""
        session = ClaudeSession()
        session.add_user_message("What is Python?")

        messages = session.get_api_messages()
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is Python?"

    def test_add_assistant_message_stores_content(self) -> None:
        """Test that add_assistant_message stores the message content."""
        session = ClaudeSession()
        session.add_user_message("What is Python?")
        session.add_assistant_message("Python is a programming language.")

        messages = session.get_api_messages()
        assert len(messages) == 2
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Python is a programming language."

    def test_messages_maintain_order(self) -> None:
        """Test that messages are returned in chronological order."""
        session = ClaudeSession()
        session.add_user_message("First question")
        session.add_assistant_message("First answer")
        session.add_user_message("Second question")
        session.add_assistant_message("Second answer")

        messages = session.get_api_messages()
        assert len(messages) == 4
        assert messages[0]["content"] == "First question"
        assert messages[1]["content"] == "First answer"
        assert messages[2]["content"] == "Second question"
        assert messages[3]["content"] == "Second answer"

    def test_get_api_messages_returns_correct_format(self) -> None:
        """Test that get_api_messages returns Claude API format."""
        session = ClaudeSession()
        session.add_user_message("Hello")
        session.add_assistant_message("Hi there!")

        messages = session.get_api_messages()

        # Should be list of dicts with role and content
        assert isinstance(messages, list)
        for msg in messages:
            assert isinstance(msg, dict)
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("user", "assistant")

    def test_reset_clears_all_messages(self) -> None:
        """Test that reset() clears all message history."""
        session = ClaudeSession()
        session.add_user_message("Question 1")
        session.add_assistant_message("Answer 1")
        session.add_user_message("Question 2")

        session.reset()

        messages = session.get_api_messages()
        assert len(messages) == 0

    def test_empty_session_returns_empty_list(self) -> None:
        """Test that empty session returns empty message list."""
        session = ClaudeSession()
        messages = session.get_api_messages()
        assert messages == []

    def test_message_count_property(self) -> None:
        """Test that message_count returns correct count."""
        session = ClaudeSession()
        assert session.message_count == 0

        session.add_user_message("Q1")
        assert session.message_count == 1

        session.add_assistant_message("A1")
        assert session.message_count == 2

    def test_session_id_is_unique(self) -> None:
        """Test that each session has a unique ID."""
        session1 = ClaudeSession()
        session2 = ClaudeSession()

        assert session1.session_id != session2.session_id

    def test_session_id_persists_after_reset(self) -> None:
        """Test that session ID remains same after reset."""
        session = ClaudeSession()
        original_id = session.session_id

        session.add_user_message("Test")
        session.reset()

        assert session.session_id == original_id


class TestClaudeSessionFollowUpWindow:
    """Tests for follow-up window timing (T027)."""

    def test_is_in_followup_window_false_initially(self) -> None:
        """Test that follow-up window is not active on new session."""
        session = ClaudeSession()
        assert not session.is_in_followup_window()

    def test_is_in_followup_window_true_after_response(self) -> None:
        """Test that follow-up window is active after receiving response."""
        session = ClaudeSession()
        session.add_user_message("Question")
        session.add_assistant_message("Answer")

        assert session.is_in_followup_window()

    def test_is_in_followup_window_false_after_timeout(self) -> None:
        """Test that follow-up window expires after timeout."""
        session = ClaudeSession(followup_window_seconds=0.1)
        session.add_user_message("Question")
        session.add_assistant_message("Answer")

        # Wait for window to expire
        time.sleep(0.15)

        assert not session.is_in_followup_window()

    def test_followup_window_resets_on_new_response(self) -> None:
        """Test that follow-up window resets when new response arrives."""
        session = ClaudeSession(followup_window_seconds=0.2)
        session.add_user_message("Q1")
        session.add_assistant_message("A1")

        # Wait partially through window
        time.sleep(0.1)

        # Add new exchange
        session.add_user_message("Q2")
        session.add_assistant_message("A2")

        # Should still be in window (reset by new response)
        assert session.is_in_followup_window()

    def test_followup_window_not_active_after_reset(self) -> None:
        """Test that reset clears follow-up window."""
        session = ClaudeSession()
        session.add_user_message("Question")
        session.add_assistant_message("Answer")

        session.reset()

        assert not session.is_in_followup_window()

    def test_default_followup_window_is_5_seconds(self) -> None:
        """Test that default follow-up window is 5 seconds."""
        session = ClaudeSession()
        assert session.followup_window_seconds == 5.0

    def test_custom_followup_window_duration(self) -> None:
        """Test that custom follow-up window duration is respected."""
        session = ClaudeSession(followup_window_seconds=10.0)
        assert session.followup_window_seconds == 10.0

    def test_last_response_time_updates_on_assistant_message(self) -> None:
        """Test that last_response_time updates when assistant responds."""
        session = ClaudeSession()

        assert session.last_response_time is None

        session.add_user_message("Question")
        assert session.last_response_time is None

        before = datetime.now(UTC)
        session.add_assistant_message("Answer")
        after = datetime.now(UTC)

        assert session.last_response_time is not None
        assert before <= session.last_response_time <= after

    def test_time_remaining_in_window(self) -> None:
        """Test that time_remaining_in_window returns correct value."""
        session = ClaudeSession(followup_window_seconds=5.0)

        # No window active
        assert session.time_remaining_in_window() == 0.0

        session.add_user_message("Q")
        session.add_assistant_message("A")

        remaining = session.time_remaining_in_window()
        assert 0 < remaining <= 5.0

    def test_extend_followup_window(self) -> None:
        """Test that extend_followup_window adds time to window."""
        session = ClaudeSession(followup_window_seconds=0.2)
        session.add_user_message("Q")
        session.add_assistant_message("A")

        # Wait until almost expired
        time.sleep(0.15)

        # Extend the window
        session.extend_followup_window(0.2)

        # Should still be in window
        time.sleep(0.1)
        assert session.is_in_followup_window()


class TestClaudeSessionHasConversationHistory:
    """Tests for conversation history tracking."""

    def test_has_history_false_on_new_session(self) -> None:
        """Test that has_history is False for new session."""
        session = ClaudeSession()
        assert not session.has_history

    def test_has_history_true_after_messages(self) -> None:
        """Test that has_history is True after adding messages."""
        session = ClaudeSession()
        session.add_user_message("Hello")
        assert session.has_history

    def test_has_history_false_after_reset(self) -> None:
        """Test that has_history is False after reset."""
        session = ClaudeSession()
        session.add_user_message("Hello")
        session.add_assistant_message("Hi!")
        session.reset()
        assert not session.has_history
