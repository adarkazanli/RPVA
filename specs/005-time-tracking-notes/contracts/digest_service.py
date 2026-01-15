"""Digest Service Contract.

Defines the interface for generating time summaries and insights.
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass
class CategoryBreakdown:
    """Time breakdown for a single category."""

    category: str
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


@dataclass
class Insight:
    """A pattern or observation about time usage."""

    type: str  # "peak_day", "category_trend", "time_pattern"
    description: str  # Natural language description
    data: dict  # Supporting data for the insight


class DigestGenerator(Protocol):
    """Interface for generating time digests."""

    def daily(self, target_date: date | None = None) -> DailyDigest:
        """Generate a daily time breakdown.

        Args:
            target_date: Date to summarize. Defaults to today.

        Returns:
            DailyDigest with category breakdown and summary

        Performance:
            Must complete in <3 seconds
        """
        ...

    def weekly(self, week_of: date | None = None) -> WeeklyDigest:
        """Generate a weekly time breakdown.

        Args:
            week_of: Any date within the target week. Defaults to current week.

        Returns:
            WeeklyDigest with category breakdown and daily totals

        Performance:
            Must complete in <5 seconds
        """
        ...


class InsightGenerator(Protocol):
    """Interface for generating time usage insights."""

    def analyze(self, weeks: int = 2) -> list[Insight]:
        """Analyze time patterns over recent weeks.

        Args:
            weeks: Number of weeks to analyze (default: 2)

        Returns:
            List of insights about time usage patterns

        Examples:
            - "You spend most productive hours in the morning"
            - "Wednesdays are your busiest work days"
            - "Health activities have increased 20% this week"
        """
        ...

    def compare_to_goal(
        self,
        category: str,
        target_hours_per_week: float,
    ) -> Insight:
        """Compare actual time to a goal.

        Args:
            category: Category to evaluate
            target_hours_per_week: Desired weekly hours

        Returns:
            Insight comparing actual vs target
        """
        ...
