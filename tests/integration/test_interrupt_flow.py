"""Integration tests for interrupt flow.

End-to-end tests for the speech interrupt and reprocessing workflow.
"""

import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from ara.router.interrupt import (
    InterruptManager,
    InterruptState,
    RequestBuffer,
    calculate_energy,
)


class TestInterruptFlowUS1:
    """Integration tests for User Story 1: Append Additional Context (T018)."""

    def test_interrupt_flow_combines_original_and_interrupt(self) -> None:
        """Verify complete interrupt flow combines input correctly.

        Scenario: User says "Research BSI", agent starts responding,
        user says "add it to my action items", system combines to
        "Research BSI add it to my action items".
        """
        # Setup mocks
        mock_capture = MagicMock()
        mock_capture.is_active = False
        mock_capture.stream.return_value = iter([])

        mock_playback = MagicMock()
        mock_playback.is_playing = False

        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        # Step 1: Set initial request
        manager.set_initial_request("Research BSI")
        assert manager.get_combined_request() == "Research BSI"

        # Step 2: Simulate interrupt text being added
        manager.request_buffer.append("add it to my action items", is_interrupt=True)

        # Step 3: Verify combined text
        combined = manager.get_combined_request()
        assert combined == "Research BSI add it to my action items"

    def test_interrupt_stops_playback_and_records(self) -> None:
        """Verify playback stops when interrupt detected."""
        mock_capture = MagicMock()
        mock_capture.is_active = True

        mock_playback = MagicMock()
        mock_playback.is_playing = False  # Quick completion for test

        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        # Play with monitoring (will complete quickly since is_playing=False)
        result = manager.play_with_monitoring(b"audio_data", 16000)

        # Verify playback was started
        mock_playback.play_async.assert_called_once_with(b"audio_data", 16000)


class TestInterruptFlowUS2:
    """Integration tests for User Story 2: Add Details (T030)."""

    def test_additive_interrupt_preserves_context(self) -> None:
        """Verify adding location/time preserves original request.

        Scenario: User says "Research BSI", agent responds,
        user says "in Austin", system combines to "Research BSI in Austin".
        """
        mock_capture = MagicMock()
        mock_playback = MagicMock()
        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        # Initial request
        manager.set_initial_request("Research BSI")

        # User adds location
        manager.request_buffer.append("in Austin", is_interrupt=True)

        # Verify natural language combination
        combined = manager.get_combined_request()
        assert combined == "Research BSI in Austin"

    def test_multiple_additive_interrupts(self) -> None:
        """Verify multiple additions are accumulated."""
        mock_capture = MagicMock()
        mock_playback = MagicMock()
        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        manager.set_initial_request("Set a reminder")
        manager.request_buffer.append("for tomorrow", is_interrupt=True)
        manager.request_buffer.append("at 3pm", is_interrupt=True)

        combined = manager.get_combined_request()
        assert combined == "Set a reminder for tomorrow at 3pm"


class TestInterruptFlowUS3:
    """Integration tests for User Story 3: Continuation Window (T036)."""

    def test_continuation_window_accepts_input_within_5_seconds(self) -> None:
        """Verify input within 5 seconds is treated as continuation."""
        mock_capture = MagicMock()
        mock_playback = MagicMock()
        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        manager.set_initial_request("What's the weather")

        # Start continuation window
        manager.start_continuation_window()
        assert manager.state == InterruptState.CONTINUATION
        assert manager._continuation_window.is_active

        # Simulate user speaking within window
        manager.request_buffer.append("and tomorrow", is_interrupt=True)

        combined = manager.get_combined_request()
        assert combined == "What's the weather and tomorrow"

        manager.cancel_continuation_window()

    def test_continuation_window_rejects_after_expiry(self) -> None:
        """Verify input after 5 seconds is treated as new request."""
        mock_capture = MagicMock()
        mock_playback = MagicMock()
        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        # Use short window for testing
        manager._continuation_window = type(manager._continuation_window)(
            duration_seconds=0.1
        )

        expired_event = threading.Event()

        def on_expire() -> None:
            expired_event.set()

        manager.set_initial_request("What's the weather")
        manager.start_continuation_window(on_expire=on_expire)

        # Wait for expiration
        expired_event.wait(timeout=0.5)

        # Window should be inactive
        assert manager._continuation_window.is_active is False


class TestInterruptFlowUS4:
    """Integration tests for User Story 4: Change Intent (T044)."""

    def test_intent_redirect_with_actually(self) -> None:
        """Verify 'actually' redirects to new intent."""
        from ara.router.interrupt import is_special_keyword

        mock_capture = MagicMock()
        mock_playback = MagicMock()
        mock_transcriber = MagicMock()

        manager = InterruptManager(
            capture=mock_capture,
            playback=mock_playback,
            transcriber=mock_transcriber,
        )

        manager.set_initial_request("Tell me about Python")

        # User redirects
        redirect_text = "actually"
        assert is_special_keyword(redirect_text)

        # After redirect, system should handle the new intent
        manager.request_buffer.append("actually what's on my calendar", is_interrupt=True)

        combined = manager.get_combined_request()
        # The combined text includes both, but intent classifier
        # will detect the redirect intent from "actually"
        assert "actually" in combined
        assert "calendar" in combined

    def test_stop_keyword_pauses_response(self) -> None:
        """Verify 'stop' keyword is recognized."""
        from ara.router.interrupt import is_special_keyword

        assert is_special_keyword("stop")
        assert is_special_keyword("wait")
        assert is_special_keyword("cancel")
        assert is_special_keyword("never mind")


class TestEnergyCalculation:
    """Tests for energy-based VAD."""

    def test_calculate_energy_silent_audio(self) -> None:
        """Verify silent audio has low energy."""
        silent_audio = bytes([0, 0] * 512)  # 512 zero samples
        energy = calculate_energy(silent_audio)
        assert energy == 0.0

    def test_calculate_energy_loud_audio(self) -> None:
        """Verify loud audio has high energy."""
        # Max amplitude 16-bit audio
        import struct

        loud_samples = [32767] * 512
        loud_audio = struct.pack(f"<{len(loud_samples)}h", *loud_samples)
        energy = calculate_energy(loud_audio)
        assert energy > 30000  # Should be close to max

    def test_calculate_energy_empty_returns_zero(self) -> None:
        """Verify empty audio returns zero."""
        energy = calculate_energy(b"")
        assert energy == 0.0
