"""Unit tests for daily digest generation.

Tests time aggregation and summary generation.
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from ara.digest.daily import CategoryBreakdown, DailyDigest, DailyDigestGenerator
from ara.notes.models import Category


class TestDailyDigestGenerator:
    """Test daily digest generation."""

    @pytest.fixture
    def mock_data_source(self) -> MagicMock:
        """Create mock data source."""
        return MagicMock()

    @pytest.fixture
    def generator(self, mock_data_source: MagicMock) -> DailyDigestGenerator:
        """Create generator with mock data source."""
        return DailyDigestGenerator(data_source=mock_data_source, user_id="test-user")

    def test_generate_empty_day(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test digest for day with no activities."""
        mock_data_source.get_activities_for_date.return_value = []

        digest = generator.generate()

        assert isinstance(digest, DailyDigest)
        assert digest.total_minutes == 0
        assert digest.activity_count == 0
        assert digest.categories == []
        assert "don't have any activities" in digest.summary

    def test_generate_single_category(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test digest with single category."""
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": 60, "category": "health"},
            {"duration_minutes": 30, "category": "health"},
        ]

        digest = generator.generate()

        assert digest.total_minutes == 90
        assert digest.activity_count == 2
        assert len(digest.categories) == 1
        assert digest.categories[0].category == Category.HEALTH
        assert digest.categories[0].total_minutes == 90

    def test_generate_multiple_categories(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test digest with multiple categories."""
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": 180, "category": "work"},
            {"duration_minutes": 60, "category": "health"},
            {"duration_minutes": 30, "category": "errands"},
        ]

        digest = generator.generate()

        assert digest.total_minutes == 270
        assert digest.activity_count == 3
        assert len(digest.categories) == 3

        # Categories should be sorted by time (descending)
        assert digest.categories[0].category == Category.WORK
        assert digest.categories[1].category == Category.HEALTH
        assert digest.categories[2].category == Category.ERRANDS

    def test_percentage_calculation(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test percentage calculation."""
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": 60, "category": "work"},
            {"duration_minutes": 40, "category": "health"},
        ]

        digest = generator.generate()

        work = next(c for c in digest.categories if c.category == Category.WORK)
        health = next(c for c in digest.categories if c.category == Category.HEALTH)

        assert work.percentage == 60.0  # 60 / 100 * 100
        assert health.percentage == 40.0  # 40 / 100 * 100

    def test_summary_formatting(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test natural language summary formatting."""
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": 180, "category": "work"},
            {"duration_minutes": 60, "category": "health"},
            {"duration_minutes": 30, "category": "errands"},
        ]

        digest = generator.generate()

        # Should mention top categories
        assert "work" in digest.summary
        assert "health" in digest.summary
        assert "Total" in digest.summary

    def test_generate_specific_date(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test generating digest for specific date."""
        target = date(2024, 1, 15)
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": 60, "category": "work"},
        ]

        digest = generator.generate(target_date=target)

        assert digest.date == target
        mock_data_source.get_activities_for_date.assert_called_once_with(target, "test-user")

    def test_generate_without_data_source(self) -> None:
        """Test generating without data source returns empty digest."""
        generator = DailyDigestGenerator(data_source=None)

        digest = generator.generate()

        assert digest.total_minutes == 0
        assert "don't have any activities" in digest.summary

    def test_handles_null_duration(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test handling activities with null duration."""
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": None, "category": "work"},
            {"duration_minutes": 60, "category": "work"},
        ]

        digest = generator.generate()

        # Should only count the non-null duration
        assert digest.total_minutes == 60

    def test_handles_invalid_category(
        self, generator: DailyDigestGenerator, mock_data_source: MagicMock
    ) -> None:
        """Test handling activities with invalid category."""
        mock_data_source.get_activities_for_date.return_value = [
            {"duration_minutes": 30, "category": "invalid_category"},
        ]

        digest = generator.generate()

        # Should fall back to uncategorized
        assert digest.categories[0].category == Category.UNCATEGORIZED


class TestCategoryBreakdown:
    """Test CategoryBreakdown dataclass."""

    def test_creation(self) -> None:
        """Test creating a breakdown."""
        breakdown = CategoryBreakdown(
            category=Category.WORK,
            total_minutes=120,
            percentage=60.0,
            activity_count=3,
        )

        assert breakdown.category == Category.WORK
        assert breakdown.total_minutes == 120
        assert breakdown.percentage == 60.0
        assert breakdown.activity_count == 3
