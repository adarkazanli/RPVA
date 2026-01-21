"""Unit tests for WaitingIndicator.

Tests the waiting indicator for Claude response feedback.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from ara.feedback import FeedbackType
from ara.feedback.waiting import WaitingIndicator


class TestWaitingIndicatorStartStop:
    """Tests for WaitingIndicator start/stop behavior."""

    @pytest.fixture
    def mock_feedback(self) -> MagicMock:
        """Create mock audio feedback."""
        mock = MagicMock()
        mock.is_enabled = True
        return mock

    def test_start_begins_playing(self, mock_feedback: MagicMock) -> None:
        """Test that start() begins playing the waiting sound."""
        indicator = WaitingIndicator(mock_feedback)
        indicator.start()

        # Give thread time to start
        time.sleep(0.1)

        assert indicator.is_playing
        indicator.stop()

    def test_stop_ends_playing(self, mock_feedback: MagicMock) -> None:
        """Test that stop() ends the waiting sound."""
        indicator = WaitingIndicator(mock_feedback)
        indicator.start()
        time.sleep(0.1)

        indicator.stop()
        time.sleep(0.1)

        assert not indicator.is_playing

    def test_is_playing_reflects_state(self, mock_feedback: MagicMock) -> None:
        """Test that is_playing accurately reflects indicator state."""
        indicator = WaitingIndicator(mock_feedback)

        assert not indicator.is_playing

        indicator.start()
        time.sleep(0.1)
        assert indicator.is_playing

        indicator.stop()
        time.sleep(0.1)
        assert not indicator.is_playing

    def test_start_is_idempotent(self, mock_feedback: MagicMock) -> None:
        """Test that calling start() multiple times is safe."""
        indicator = WaitingIndicator(mock_feedback)

        indicator.start()
        indicator.start()  # Should not raise or create multiple threads
        indicator.start()

        time.sleep(0.1)
        assert indicator.is_playing

        indicator.stop()

    def test_stop_is_idempotent(self, mock_feedback: MagicMock) -> None:
        """Test that calling stop() multiple times is safe."""
        indicator = WaitingIndicator(mock_feedback)

        indicator.start()
        time.sleep(0.1)

        indicator.stop()
        indicator.stop()  # Should not raise
        indicator.stop()

        assert not indicator.is_playing

    def test_stop_without_start_is_safe(self, mock_feedback: MagicMock) -> None:
        """Test that stop() without start() is safe."""
        indicator = WaitingIndicator(mock_feedback)
        indicator.stop()  # Should not raise
        assert not indicator.is_playing

    def test_plays_claude_waiting_feedback(self, mock_feedback: MagicMock) -> None:
        """Test that the correct feedback type is played."""
        indicator = WaitingIndicator(mock_feedback)
        indicator.start()

        # Give time for at least one play
        time.sleep(0.2)

        indicator.stop()

        # Verify play was called with CLAUDE_WAITING type
        mock_feedback.play.assert_called()
        call_args = mock_feedback.play.call_args_list[0]
        assert call_args[0][0] == FeedbackType.CLAUDE_WAITING

    def test_loops_until_stopped(self, mock_feedback: MagicMock) -> None:
        """Test that the sound loops until stopped."""
        indicator = WaitingIndicator(mock_feedback, loop_interval=0.05)
        indicator.start()

        # Let it loop a few times
        time.sleep(0.2)

        indicator.stop()

        # Should have been called multiple times
        assert mock_feedback.play.call_count >= 2


class TestWaitingIndicatorContextManager:
    """Tests for WaitingIndicator context manager usage."""

    @pytest.fixture
    def mock_feedback(self) -> MagicMock:
        """Create mock audio feedback."""
        mock = MagicMock()
        mock.is_enabled = True
        return mock

    def test_context_manager_starts_and_stops(
        self, mock_feedback: MagicMock
    ) -> None:
        """Test that context manager properly starts and stops."""
        indicator = WaitingIndicator(mock_feedback)

        with indicator:
            time.sleep(0.1)
            assert indicator.is_playing

        time.sleep(0.1)
        assert not indicator.is_playing

    def test_context_manager_stops_on_exception(
        self, mock_feedback: MagicMock
    ) -> None:
        """Test that context manager stops on exception."""
        indicator = WaitingIndicator(mock_feedback)

        with pytest.raises(ValueError):
            with indicator:
                time.sleep(0.1)
                raise ValueError("Test error")

        time.sleep(0.1)
        assert not indicator.is_playing


class TestWaitingIndicatorDisabled:
    """Tests for WaitingIndicator when feedback is disabled."""

    def test_does_not_play_when_feedback_disabled(self) -> None:
        """Test that nothing plays when feedback is disabled."""
        mock_feedback = MagicMock()
        mock_feedback.is_enabled = False

        indicator = WaitingIndicator(mock_feedback)
        indicator.start()
        time.sleep(0.1)
        indicator.stop()

        # Should not have called play since feedback is disabled
        mock_feedback.play.assert_not_called()
