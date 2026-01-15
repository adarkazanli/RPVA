"""Daily digest generation.

Provides daily time breakdown by category.
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from ara.notes.models import Category

logger = logging.getLogger(__name__)


@dataclass
class CategoryBreakdown:
    """Time breakdown for a single category."""

    category: Category
    total_minutes: int
    percentage: float
    activity_count: int


@dataclass
class DailyDigest:
    """Summary of a single day's activities."""

    date: date
    total_minutes: int
    categories: list[CategoryBreakdown]
    activity_count: int
    summary: str  # Natural language summary for TTS


class ActivityDataSource(Protocol):
    """Protocol for fetching activity data."""

    def get_activities_for_date(self, target_date: date, user_id: str) -> list[dict[str, Any]]:
        """Get all activities for a specific date."""
        ...


class DailyDigestGenerator:
    """Generates daily time digests.

    Aggregates activities by category and generates natural language summaries.
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

    def generate(self, target_date: date | None = None) -> DailyDigest:
        """Generate a daily time breakdown.

        Args:
            target_date: Date to summarize. Defaults to today.

        Returns:
            DailyDigest with category breakdown and summary
        """
        target_date = target_date or date.today()

        if not self._data_source:
            return DailyDigest(
                date=target_date,
                total_minutes=0,
                categories=[],
                activity_count=0,
                summary="I don't have any activities tracked for today yet.",
            )

        # Fetch activities
        activities = self._data_source.get_activities_for_date(target_date, self._user_id)

        if not activities:
            return DailyDigest(
                date=target_date,
                total_minutes=0,
                categories=[],
                activity_count=0,
                summary="I don't have any activities tracked for today yet.",
            )

        # Aggregate by category
        category_totals: dict[Category, int] = {}
        category_counts: dict[Category, int] = {}

        for activity in activities:
            duration = activity.get("duration_minutes", 0) or 0
            category_str = activity.get("category", "uncategorized")
            try:
                category = Category(category_str)
            except ValueError:
                category = Category.UNCATEGORIZED

            category_totals[category] = category_totals.get(category, 0) + duration
            category_counts[category] = category_counts.get(category, 0) + 1

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
        summary = self._generate_summary(target_date, breakdowns, total_minutes)

        return DailyDigest(
            date=target_date,
            total_minutes=total_minutes,
            categories=breakdowns,
            activity_count=activity_count,
            summary=summary,
        )

    def _generate_summary(
        self,
        target_date: date,
        breakdowns: list[CategoryBreakdown],
        total_minutes: int,
    ) -> str:
        """Generate natural language summary.

        Args:
            target_date: Date being summarized
            breakdowns: Category breakdowns sorted by time
            total_minutes: Total tracked time

        Returns:
            Natural language summary for TTS
        """
        if not breakdowns:
            return "I don't have any activities tracked for today yet."

        # Format total time
        hours = total_minutes // 60
        minutes = total_minutes % 60

        if hours > 0 and minutes > 0:
            total_str = f"{hours} hour{'s' if hours > 1 else ''} and {minutes} minutes"
        elif hours > 0:
            total_str = f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            total_str = f"{minutes} minute{'s' if minutes > 1 else ''}"

        # Build category breakdown
        parts = []
        for breakdown in breakdowns[:3]:  # Top 3 categories
            cat_hours = breakdown.total_minutes // 60
            cat_mins = breakdown.total_minutes % 60

            if cat_hours > 0 and cat_mins > 0:
                time_str = f"{cat_hours} hour{'s' if cat_hours > 1 else ''} and {cat_mins} minutes"
            elif cat_hours > 0:
                time_str = f"{cat_hours} hour{'s' if cat_hours > 1 else ''}"
            else:
                time_str = f"{cat_mins} minute{'s' if cat_mins > 1 else ''}"

            parts.append(f"{time_str} on {breakdown.category.value}")

        # Construct sentence
        if len(parts) == 1:
            breakdown_str = parts[0]
        elif len(parts) == 2:
            breakdown_str = f"{parts[0]} and {parts[1]}"
        else:
            breakdown_str = f"{parts[0]}, {parts[1]}, and {parts[2]}"

        is_today = target_date == date.today()
        day_ref = "Today" if is_today else target_date.strftime("%A")

        return f"{day_ref} you spent {breakdown_str}. Total: {total_str}."


__all__ = ["DailyDigest", "DailyDigestGenerator", "CategoryBreakdown", "ActivityDataSource"]
