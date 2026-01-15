"""Tests for insight generation."""

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from ara.digest.insights import Insight, InsightGenerator
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


class TestInsightGenerator:
    """Tests for InsightGenerator."""

    def test_analyze_no_data_source(self) -> None:
        """Returns empty list when no data source."""
        generator = InsightGenerator()
        insights = generator.analyze()

        assert insights == []

    def test_analyze_insufficient_data(self) -> None:
        """Returns empty list when insufficient activities."""
        activities = [
            {"duration_minutes": 60, "category": "work", "start_time": datetime.now(UTC)},
        ]
        data_source = MockDataSource(activities)
        generator = InsightGenerator(data_source=data_source)
        insights = generator.analyze()

        assert insights == []

    def test_analyze_finds_peak_day(self) -> None:
        """Identifies busiest day of week."""
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        tuesday = monday + timedelta(days=1)

        activities = [
            # Monday: 60 min
            {"duration_minutes": 60, "category": "work", "start_time": datetime(monday.year, monday.month, monday.day, 9, 0, tzinfo=UTC)},
            # Tuesday: 180 min (busiest)
            {"duration_minutes": 120, "category": "work", "start_time": datetime(tuesday.year, tuesday.month, tuesday.day, 9, 0, tzinfo=UTC)},
            {"duration_minutes": 60, "category": "health", "start_time": datetime(tuesday.year, tuesday.month, tuesday.day, 18, 0, tzinfo=UTC)},
            # More to meet minimum
            {"duration_minutes": 30, "category": "work", "start_time": datetime(monday.year, monday.month, monday.day, 14, 0, tzinfo=UTC)},
            {"duration_minutes": 30, "category": "personal", "start_time": datetime(monday.year, monday.month, monday.day, 20, 0, tzinfo=UTC)},
        ]
        data_source = MockDataSource(activities)
        generator = InsightGenerator(data_source=data_source)
        insights = generator.analyze()

        peak_insight = next((i for i in insights if i.type == "peak_day"), None)
        assert peak_insight is not None
        assert "Tuesday" in peak_insight.description
        assert peak_insight.data["day"] == "Tuesday"

    def test_analyze_finds_category_trend(self) -> None:
        """Identifies dominant category."""
        today = date.today()
        activities = [
            {"duration_minutes": 120, "category": "work", "start_time": datetime(today.year, today.month, today.day, 9, 0, tzinfo=UTC)},
            {"duration_minutes": 60, "category": "work", "start_time": datetime(today.year, today.month, today.day, 14, 0, tzinfo=UTC)},
            {"duration_minutes": 30, "category": "health", "start_time": datetime(today.year, today.month, today.day, 18, 0, tzinfo=UTC)},
            {"duration_minutes": 20, "category": "personal", "start_time": datetime(today.year, today.month, today.day, 20, 0, tzinfo=UTC)},
            {"duration_minutes": 10, "category": "errands", "start_time": datetime(today.year, today.month, today.day, 21, 0, tzinfo=UTC)},
        ]
        data_source = MockDataSource(activities)
        generator = InsightGenerator(data_source=data_source)
        insights = generator.analyze()

        category_insight = next((i for i in insights if i.type == "category_trend"), None)
        assert category_insight is not None
        assert "work" in category_insight.description
        assert category_insight.data["category"] == "work"

    def test_compare_to_goal_exceeding(self) -> None:
        """Compares actual time to goal when exceeding."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        activities = [
            {"duration_minutes": 180, "category": "health", "start_time": datetime(week_start.year, week_start.month, week_start.day, 9, 0, tzinfo=UTC)},
            {"duration_minutes": 120, "category": "health", "start_time": datetime(week_start.year, week_start.month, week_start.day + 1, 9, 0, tzinfo=UTC)},
        ]
        data_source = MockDataSource(activities)
        generator = InsightGenerator(data_source=data_source)

        insight = generator.compare_to_goal(Category.HEALTH, target_hours_per_week=4.0)

        assert insight.type == "goal_comparison"
        assert "exceeding" in insight.description.lower() or "great" in insight.description.lower()
        assert insight.data["actual_hours"] == 5.0

    def test_compare_to_goal_below_target(self) -> None:
        """Compares actual time to goal when below."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        activities = [
            {"duration_minutes": 60, "category": "health", "start_time": datetime(week_start.year, week_start.month, week_start.day, 9, 0, tzinfo=UTC)},
        ]
        data_source = MockDataSource(activities)
        generator = InsightGenerator(data_source=data_source)

        insight = generator.compare_to_goal(Category.HEALTH, target_hours_per_week=5.0)

        assert insight.type == "goal_comparison"
        assert "need" in insight.description.lower() or "more" in insight.description.lower()
        assert insight.data["actual_hours"] == 1.0
        assert insight.data["target_hours"] == 5.0

    def test_compare_to_goal_no_data_source(self) -> None:
        """Handles missing data source gracefully."""
        generator = InsightGenerator()
        insight = generator.compare_to_goal(Category.WORK, target_hours_per_week=40.0)

        assert insight.type == "goal_comparison"
        assert "don't have enough data" in insight.description.lower()

    def test_insight_dataclass(self) -> None:
        """Insight dataclass stores correctly."""
        insight = Insight(
            type="test_type",
            description="Test description",
            data={"key": "value"},
        )

        assert insight.type == "test_type"
        assert insight.description == "Test description"
        assert insight.data == {"key": "value"}
