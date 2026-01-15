"""Unit tests for stop keyword handling in transcripts."""

import pytest


class TestStopKeywordStripping:
    """Tests for stripping 'done porcupine' stop keyword from transcripts."""

    @pytest.fixture
    def stop_keyword(self) -> str:
        """The stop keyword used by the orchestrator."""
        return "done porcupine"

    def test_strip_stop_keyword_at_end(self, stop_keyword: str) -> None:
        """Test stripping stop keyword at the end of transcript."""
        transcript = "I met with John about the budget done porcupine"

        if transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "I met with John about the budget"

    def test_strip_stop_keyword_with_punctuation(self, stop_keyword: str) -> None:
        """Test stripping stop keyword with trailing punctuation."""
        transcript = "I met with John about the budget. done porcupine"

        if transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()
            transcript = transcript.rstrip(".,;:!?")

        assert transcript == "I met with John about the budget"

    def test_no_strip_when_keyword_missing(self, stop_keyword: str) -> None:
        """Test that normal transcripts are not modified."""
        transcript = "I met with John about the budget"

        if transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "I met with John about the budget"

    def test_case_insensitive_match(self, stop_keyword: str) -> None:
        """Test that stop keyword matching is case-insensitive."""
        transcript = "My note here Done Porcupine"

        if transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "My note here"

    def test_partial_keyword_not_stripped(self, stop_keyword: str) -> None:
        """Test that partial matches are not stripped."""
        transcript = "I met with John who is done"

        if transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        assert transcript == "I met with John who is done"

    def test_keyword_in_middle_not_stripped(self, stop_keyword: str) -> None:
        """Test that keyword in middle is not stripped."""
        transcript = "I said done porcupine and then continued talking"

        if transcript.lower().endswith(stop_keyword):
            transcript = transcript[: -len(stop_keyword)].strip()

        # Should not be modified since keyword is in the middle
        assert transcript == "I said done porcupine and then continued talking"
