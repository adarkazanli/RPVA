"""Unit tests for stop keyword and note-taking mode handling."""

import pytest


class TestStopKeywordStripping:
    """Tests for stripping 'done porcupine' stop keyword from transcripts (note mode only)."""

    @pytest.fixture
    def stop_keyword(self) -> str:
        """The stop keyword used by the orchestrator."""
        return "done porcupine"

    def test_strip_stop_keyword_at_end(self, stop_keyword: str) -> None:
        """Test stripping stop keyword at the end of transcript."""
        transcript = "Take note I met with John about the budget done porcupine"
        is_note_mode = True

        if is_note_mode and transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "Take note I met with John about the budget"

    def test_strip_stop_keyword_with_punctuation(self, stop_keyword: str) -> None:
        """Test stripping stop keyword with trailing punctuation."""
        transcript = "Take note I met with John about the budget. done porcupine"
        is_note_mode = True

        if is_note_mode and transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()
            transcript = transcript.rstrip(".,;:!?")

        assert transcript == "Take note I met with John about the budget"

    def test_no_strip_when_not_note_mode(self, stop_keyword: str) -> None:
        """Test that keyword is not stripped outside note mode."""
        transcript = "What is done porcupine"
        is_note_mode = False

        if is_note_mode and transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        # Should not be modified since not in note mode
        assert transcript == "What is done porcupine"

    def test_no_strip_when_keyword_missing(self, stop_keyword: str) -> None:
        """Test that normal transcripts are not modified."""
        transcript = "Take note I met with John about the budget"
        is_note_mode = True

        if is_note_mode and transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "Take note I met with John about the budget"

    def test_case_insensitive_match(self, stop_keyword: str) -> None:
        """Test that stop keyword matching is case-insensitive."""
        transcript = "Take note my note here Done Porcupine"
        is_note_mode = True

        if is_note_mode and transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "Take note my note here"

    def test_partial_keyword_not_stripped(self, stop_keyword: str) -> None:
        """Test that partial matches are not stripped."""
        transcript = "Take note I met with John who is done"
        is_note_mode = True

        if is_note_mode and transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "Take note I met with John who is done"


class TestNoteTriggerDetection:
    """Tests for note-taking trigger phrase detection."""

    @pytest.fixture
    def note_triggers(self) -> list[str]:
        """Note-taking trigger phrases."""
        return ["take note", "take a note", "note that", "remember that"]

    def test_detect_take_note(self, note_triggers: list[str]) -> None:
        """Test detection of 'take note' trigger."""
        text = "Take note I met with John today"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is True

    def test_detect_take_a_note(self, note_triggers: list[str]) -> None:
        """Test detection of 'take a note' trigger."""
        text = "Take a note about the budget meeting"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is True

    def test_detect_note_that(self, note_triggers: list[str]) -> None:
        """Test detection of 'note that' trigger."""
        text = "Note that Sarah called about the project"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is True

    def test_detect_remember_that(self, note_triggers: list[str]) -> None:
        """Test detection of 'remember that' trigger."""
        text = "Remember that I need to call mom tomorrow"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is True

    def test_no_detection_for_question(self, note_triggers: list[str]) -> None:
        """Test that questions are not detected as notes."""
        text = "What time is it"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is False

    def test_no_detection_for_timer(self, note_triggers: list[str]) -> None:
        """Test that timer commands are not detected as notes."""
        text = "Set a timer for 5 minutes"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is False

    def test_case_insensitive_detection(self, note_triggers: list[str]) -> None:
        """Test that trigger detection is case-insensitive."""
        text = "TAKE NOTE this is important"
        is_note = any(text.lower().startswith(phrase) for phrase in note_triggers)
        assert is_note is True
