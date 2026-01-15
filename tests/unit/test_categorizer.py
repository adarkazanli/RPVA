"""Unit tests for auto-categorization.

Tests keyword-based categorization for notes and activities.
"""

import pytest

from ara.notes.categorizer import categorize, categorize_with_confidence
from ara.notes.models import Category


class TestCategorize:
    """Test keyword-based categorization."""

    # Health category tests
    @pytest.mark.parametrize(
        "text",
        [
            "starting my workout",
            "going to the gym",
            "exercise for 30 minutes",
            "yoga session at home",
            "meditation time",
            "doctor appointment at 3pm",
            "running in the park",
            "swimming laps",
        ],
    )
    def test_health_category(self, text: str) -> None:
        """Test health-related texts are categorized correctly."""
        assert categorize(text) == Category.HEALTH

    # Work category tests
    @pytest.mark.parametrize(
        "text",
        [
            "meeting with the team",
            "project deadline tomorrow",
            "client call at noon",
            "sprint planning session",
            "standup meeting",
            "working on the report",
            "presentation for the boss",
            "coding the new feature",
        ],
    )
    def test_work_category(self, text: str) -> None:
        """Test work-related texts are categorized correctly."""
        assert categorize(text) == Category.WORK

    # Errands category tests
    @pytest.mark.parametrize(
        "text",
        [
            "pick up groceries",
            "shopping at the mall",
            "going to the pharmacy",
            "drop off the package",
            "bank appointment",
            "errands around town",
            "dry cleaning pickup",
        ],
    )
    def test_errands_category(self, text: str) -> None:
        """Test errand-related texts are categorized correctly."""
        assert categorize(text) == Category.ERRANDS

    # Personal category tests
    @pytest.mark.parametrize(
        "text",
        [
            "dinner with family",
            "lunch with a friend",
            "movie night",
            "game time",
            "reading a book",
            "cooking dinner",
            "birthday party",
            "watching netflix",
        ],
    )
    def test_personal_category(self, text: str) -> None:
        """Test personal-related texts are categorized correctly."""
        assert categorize(text) == Category.PERSONAL

    # Uncategorized tests
    @pytest.mark.parametrize(
        "text",
        [
            "random text with no keywords",
            "something else entirely",
            "xyz abc 123",
        ],
    )
    def test_uncategorized(self, text: str) -> None:
        """Test texts without matching keywords are uncategorized."""
        assert categorize(text) == Category.UNCATEGORIZED

    def test_case_insensitive(self) -> None:
        """Test categorization is case insensitive."""
        assert categorize("STARTING MY WORKOUT") == Category.HEALTH
        assert categorize("Meeting With Team") == Category.WORK
        assert categorize("GYM SESSION") == Category.HEALTH


class TestCategorizeWithConfidence:
    """Test categorization with confidence scores."""

    def test_single_keyword_match(self) -> None:
        """Test confidence for single keyword match."""
        category, confidence = categorize_with_confidence("going to the gym")
        assert category == Category.HEALTH
        assert 0.7 <= confidence <= 0.85

    def test_multiple_keyword_matches(self) -> None:
        """Test higher confidence for multiple keyword matches."""
        # "workout" and "exercise" both match health
        category, confidence = categorize_with_confidence("workout exercise routine")
        assert category == Category.HEALTH
        assert confidence > 0.8

    def test_no_match_returns_uncategorized(self) -> None:
        """Test uncategorized with base confidence."""
        category, confidence = categorize_with_confidence("random xyz text")
        assert category == Category.UNCATEGORIZED
        assert confidence == 0.5

    def test_competing_categories(self) -> None:
        """Test that the category with most matches wins."""
        # "meeting" is work, "gym" is health
        # Only one keyword each, should pick first match
        category, _ = categorize_with_confidence("meeting at the gym")
        # Either health or work is acceptable since they have equal matches
        assert category in (Category.HEALTH, Category.WORK)
