"""Insight generation for time patterns.

Analyzes time usage patterns over multiple weeks.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from ara.notes.models import Category

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """A pattern or observation about time usage."""

    type: str  # "peak_day", "category_trend", "time_pattern"
    description: str  # Natural language description
    data: dict[str, Any]  # Supporting data for the insight


class ActivityDataSource(Protocol):
    """Protocol for fetching activity data."""

    def get_activities_for_date_range(
        self, start_date: date, end_date: date, user_id: str
    ) -> list[dict[str, Any]]:
        """Get activities in date range."""
        ...


class InsightGenerator:
    """Generates insights about time usage patterns.

    Analyzes data over multiple weeks to identify trends.
    """

    def __init__(
        self,
        data_source: ActivityDataSource | None = None,
        user_id: str = "default",
    ) -> None:
        """Initialize insight generator.

        Args:
            data_source: Source for activity data
            user_id: User ID for filtering activities
        """
        self._data_source = data_source
        self._user_id = user_id

    def analyze(self, weeks: int = 2) -> list[Insight]:
        """Analyze time patterns over recent weeks.

        Args:
            weeks: Number of weeks to analyze (default: 2)

        Returns:
            List of insights about time usage patterns
        """
        if not self._data_source:
            return []

        # Calculate date range
        today = date.today()
        start_date = today - timedelta(weeks=weeks * 7)

        # Fetch activities
        activities = self._data_source.get_activities_for_date_range(
            start_date, today, self._user_id
        )

        if len(activities) < 5:  # Need minimum data for insights
            return []

        insights: list[Insight] = []

        # Analyze peak day
        peak_day_insight = self._analyze_peak_day(activities)
        if peak_day_insight:
            insights.append(peak_day_insight)

        # Analyze category distribution
        category_insight = self._analyze_categories(activities)
        if category_insight:
            insights.append(category_insight)

        return insights

    def _analyze_peak_day(self, activities: list[dict[str, Any]]) -> Insight | None:
        """Find the busiest day of the week."""
        daily_totals: dict[str, int] = {}

        for activity in activities:
            duration = activity.get("duration_minutes", 0) or 0
            start_time = activity.get("start_time")

            if start_time:
                day_name = start_time.strftime("%A")
                daily_totals[day_name] = daily_totals.get(day_name, 0) + duration

        if not daily_totals:
            return None

        peak_day = max(daily_totals, key=lambda d: daily_totals[d])
        peak_minutes = daily_totals[peak_day]
        peak_hours = peak_minutes // 60

        if peak_hours < 1:
            return None

        return Insight(
            type="peak_day",
            description=f"{peak_day}s are your busiest days with an average of {peak_hours} hours tracked.",
            data={"day": peak_day, "average_minutes": peak_minutes},
        )

    def _analyze_categories(self, activities: list[dict[str, Any]]) -> Insight | None:
        """Analyze category distribution."""
        category_totals: dict[Category, int] = {}

        for activity in activities:
            duration = activity.get("duration_minutes", 0) or 0
            category_str = activity.get("category", "uncategorized")

            try:
                category = Category(category_str)
            except ValueError:
                category = Category.UNCATEGORIZED

            category_totals[category] = category_totals.get(category, 0) + duration

        if not category_totals:
            return None

        top_category = max(category_totals, key=lambda c: category_totals[c])
        total_minutes = sum(category_totals.values())
        percentage = (
            (category_totals[top_category] / total_minutes * 100) if total_minutes > 0 else 0
        )

        if percentage < 30:  # Only report if category is significant
            return None

        return Insight(
            type="category_trend",
            description=f"You spend most of your time on {top_category.value} ({percentage:.0f}% of tracked time).",
            data={"category": top_category.value, "percentage": percentage},
        )

    def compare_to_goal(
        self,
        category: Category,
        target_hours_per_week: float,
    ) -> Insight:
        """Compare actual time to a goal.

        Args:
            category: Category to evaluate
            target_hours_per_week: Desired weekly hours

        Returns:
            Insight comparing actual vs target
        """
        if not self._data_source:
            return Insight(
                type="goal_comparison",
                description=f"I don't have enough data to compare your {category.value} time to your goal.",
                data={"category": category.value, "target_hours": target_hours_per_week},
            )

        # Get last week's data
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = today

        activities = self._data_source.get_activities_for_date_range(
            week_start, week_end, self._user_id
        )

        # Sum category time
        category_minutes = sum(
            (a.get("duration_minutes", 0) or 0)
            for a in activities
            if a.get("category") == category.value
        )
        actual_hours = category_minutes / 60

        # Compare
        target_minutes = target_hours_per_week * 60
        difference = actual_hours - target_hours_per_week
        percentage_of_goal = (category_minutes / target_minutes * 100) if target_minutes > 0 else 0

        if difference >= 0:
            description = f"Great! You've spent {actual_hours:.1f} hours on {category.value} this week, exceeding your goal of {target_hours_per_week} hours."
        else:
            remaining = target_hours_per_week - actual_hours
            description = f"You've spent {actual_hours:.1f} hours on {category.value} this week. You need {remaining:.1f} more hours to reach your {target_hours_per_week}-hour goal."

        return Insight(
            type="goal_comparison",
            description=description,
            data={
                "category": category.value,
                "actual_hours": actual_hours,
                "target_hours": target_hours_per_week,
                "percentage_of_goal": percentage_of_goal,
            },
        )


__all__ = ["Insight", "InsightGenerator"]
