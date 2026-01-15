"""Tests for weekly digest generation."""

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from ara.digest.weekly import WeeklyDigestGenerator
from ara.notes.models import Category

UTC = ZoneInfo("UTC")


class MockDataSource:
    """Mock data source for testing."""

    def __init__(self, activities: list[dict[str, Any]] | None = None) -> None:
        self.activities = activities or []

    def get_activities_for_date_range(
        self, _start_date: date, _end_date: date, _user_id: str
    ) -> list[dict[str, Any]]:
        """Return mock activities."""
        return self.activities


class TestWeeklyDigestGenerator:
    """Tests for WeeklyDigestGenerator."""

    def test_generate_no_data_source(self) -> None:
        """Returns empty digest when no data source."""
        generator = WeeklyDigestGenerator()
        digest = generator.generate()

        assert digest.total_minutes == 0
        assert digest.categories == []
        assert digest.activity_count == 0
        assert "don't have enough" in digest.summary.lower()

    def test_generate_empty_activities(self) -> None:
        """Returns empty digest when no activities."""
        data_source = MockDataSource([])
        generator = WeeklyDigestGenerator(data_source=data_source)
        digest = generator.generate()

        assert digest.total_minutes == 0
        assert digest.categories == []

    def test_generate_with_activities(self) -> None:
        """Generates digest with category breakdown."""
        today = date.today()
        activities = [
            {
                "duration_minutes": 60,
                "category": "work",
                "start_time": datetime(today.year, today.month, today.day, 9, 0, tzinfo=UTC),
            },
            {
                "duration_minutes": 30,
                "category": "work",
                "start_time": datetime(today.year, today.month, today.day, 10, 0, tzinfo=UTC),
            },
            {
                "duration_minutes": 45,
                "category": "health",
                "start_time": datetime(today.year, today.month, today.day, 18, 0, tzinfo=UTC),
            },
        ]
        data_source = MockDataSource(activities)
        generator = WeeklyDigestGenerator(data_source=data_source)
        digest = generator.generate()

        assert digest.total_minutes == 135
        assert digest.activity_count == 3
        assert len(digest.categories) == 2
        assert digest.categories[0].category == Category.WORK
        assert digest.categories[0].total_minutes == 90

    def test_generate_calculates_week_boundaries(self) -> None:
        """Calculates correct week start/end."""
        generator = WeeklyDigestGenerator()
        digest = generator.generate()

        # Week should be Monday to Sunday
        assert digest.week_start.weekday() == 0  # Monday
        assert digest.week_end.weekday() == 6  # Sunday
        assert (digest.week_end - digest.week_start).days == 6

    def test_generate_for_specific_date(self) -> None:
        """Can generate digest for specific week."""
        specific_date = date(2024, 1, 15)  # A Monday
        generator = WeeklyDigestGenerator()
        digest = generator.generate(week_of=specific_date)

        assert digest.week_start == date(2024, 1, 15)
        assert digest.week_end == date(2024, 1, 21)

    def test_daily_totals_aggregation(self) -> None:
        """Aggregates time by day of week."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        activities = [
            {
                "duration_minutes": 60,
                "category": "work",
                "start_time": datetime(monday.year, monday.month, monday.day, 9, 0, tzinfo=UTC),
            },
            {
                "duration_minutes": 120,
                "category": "work",
                "start_time": datetime(monday.year, monday.month, monday.day, 14, 0, tzinfo=UTC),
            },
        ]
        data_source = MockDataSource(activities)
        generator = WeeklyDigestGenerator(data_source=data_source)
        digest = generator.generate()

        assert digest.daily_totals["Monday"] == 180

    def test_summary_includes_total_hours(self) -> None:
        """Summary mentions total hours tracked."""
        today = date.today()
        activities = [
            {
                "duration_minutes": 180,
                "category": "work",
                "start_time": datetime(today.year, today.month, today.day, 9, 0, tzinfo=UTC),
            },
        ]
        data_source = MockDataSource(activities)
        generator = WeeklyDigestGenerator(data_source=data_source)
        digest = generator.generate()

        assert "3 hours" in digest.summary

    def test_handles_uncategorized_activities(self) -> None:
        """Handles activities with unknown category."""
        today = date.today()
        activities = [
            {
                "duration_minutes": 60,
                "category": "unknown_category",
                "start_time": datetime(today.year, today.month, today.day, 9, 0, tzinfo=UTC),
            },
        ]
        data_source = MockDataSource(activities)
        generator = WeeklyDigestGenerator(data_source=data_source)
        digest = generator.generate()

        assert digest.categories[0].category == Category.UNCATEGORIZED
