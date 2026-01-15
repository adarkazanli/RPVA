"""Weekly digest generation.

Provides weekly time breakdown with trends and patterns.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Protocol

from ara.notes.models import Category

from .daily import CategoryBreakdown

logger = logging.getLogger(__name__)


@dataclass
class WeeklyDigest:
    """Summary of a week's activities."""

    week_start: date
    week_end: date
    total_minutes: int
    categories: list[CategoryBreakdown]
    daily_totals: dict[str, int]  # day_name -> minutes
    activity_count: int
    summary: str  # Natural language summary for TTS


class ActivityDataSource(Protocol):
    """Protocol for fetching activity data."""

    def get_activities_for_date_range(
        self, start_date: date, end_date: date, user_id: str
    ) -> list[dict[str, Any]]:
        """Get activities in date range."""
        ...


class WeeklyDigestGenerator:
    """Generates weekly time digests with patterns.

    Aggregates activities by category and day of week.
    """

    def __init__(
        self,
        data_source: ActivityDataSource | None = None,
        user_id: str = "default",
    ) -> None:
        """Initialize digest generator.

        Args:
            data_source: Source for activity data
            user_id: User ID for filtering activities
        """
        self._data_source = data_source
        self._user_id = user_id

    def generate(self, week_of: date | None = None) -> WeeklyDigest:
        """Generate a weekly time breakdown.

        Args:
            week_of: Any date within the target week. Defaults to current week.

        Returns:
            WeeklyDigest with category breakdown and daily totals
        """
        # Calculate week boundaries (Monday to Sunday)
        reference_date = week_of or date.today()
        days_since_monday = reference_date.weekday()
        week_start = reference_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)

        if not self._data_source:
            return WeeklyDigest(
                week_start=week_start,
                week_end=week_end,
                total_minutes=0,
                categories=[],
                daily_totals={},
                activity_count=0,
                summary="I don't have enough activity data for a weekly summary yet.",
            )

        # Fetch activities
        activities = self._data_source.get_activities_for_date_range(
            week_start, week_end, self._user_id
        )

        if not activities:
            return WeeklyDigest(
                week_start=week_start,
                week_end=week_end,
                total_minutes=0,
                categories=[],
                daily_totals={},
                activity_count=0,
                summary="I don't have enough activity data for a weekly summary yet.",
            )

        # Aggregate by category
        category_totals: dict[Category, int] = {}
        category_counts: dict[Category, int] = {}

        # Aggregate by day of week
        daily_totals: dict[str, int] = {
            "Monday": 0,
            "Tuesday": 0,
            "Wednesday": 0,
            "Thursday": 0,
            "Friday": 0,
            "Saturday": 0,
            "Sunday": 0,
        }

        for activity in activities:
            duration = activity.get("duration_minutes", 0) or 0
            category_str = activity.get("category", "uncategorized")
            start_time = activity.get("start_time")

            try:
                category = Category(category_str)
            except ValueError:
                category = Category.UNCATEGORIZED

            category_totals[category] = category_totals.get(category, 0) + duration
            category_counts[category] = category_counts.get(category, 0) + 1

            # Add to daily total
            if start_time:
                day_name = start_time.strftime("%A")
                daily_totals[day_name] = daily_totals.get(day_name, 0) + duration

        # Calculate total and percentages
        total_minutes = sum(category_totals.values())
        activity_count = len(activities)

        breakdowns: list[CategoryBreakdown] = []
        for category, minutes in sorted(
            category_totals.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            percentage = (minutes / total_minutes * 100) if total_minutes > 0 else 0
            breakdowns.append(
                CategoryBreakdown(
                    category=category,
                    total_minutes=minutes,
                    percentage=percentage,
                    activity_count=category_counts[category],
                )
            )

        # Generate natural language summary
        summary = self._generate_summary(breakdowns, daily_totals, total_minutes)

        return WeeklyDigest(
            week_start=week_start,
            week_end=week_end,
            total_minutes=total_minutes,
            categories=breakdowns,
            daily_totals=daily_totals,
            activity_count=activity_count,
            summary=summary,
        )

    def _generate_summary(
        self,
        breakdowns: list[CategoryBreakdown],
        daily_totals: dict[str, int],
        total_minutes: int,
    ) -> str:
        """Generate natural language summary with patterns."""
        if not breakdowns:
            return "I don't have enough activity data for a weekly summary yet."

        # Format total time
        hours = total_minutes // 60

        # Find busiest day
        busiest_day = max(daily_totals, key=lambda d: daily_totals[d])
        busiest_minutes = daily_totals[busiest_day]

        # Build category summary (top 2)
        parts = []
        for breakdown in breakdowns[:2]:
            cat_hours = breakdown.total_minutes // 60
            parts.append(f"{cat_hours} hours on {breakdown.category.value}")

        category_str = parts[0] if len(parts) == 1 else f"{parts[0]} and {parts[1]}"

        # Construct summary
        summary_parts = [f"This week you tracked {hours} hours total."]
        summary_parts.append(f"You spent {category_str}.")

        if busiest_minutes > 0:
            busiest_hours = busiest_minutes // 60
            summary_parts.append(f"{busiest_day} was your busiest day with {busiest_hours} hours.")

        return " ".join(summary_parts)


__all__ = ["WeeklyDigest", "WeeklyDigestGenerator"]
