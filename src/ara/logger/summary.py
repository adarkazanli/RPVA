"""Daily summary generation for conversation logs.

Generates aggregated statistics and action items from daily interactions.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from .interaction import Interaction
from .storage import InteractionStorage


@dataclass
class ActionItem:
    """An action item extracted from interactions."""

    text: str
    source_transcript: str


@dataclass
class DailySummary:
    """Aggregated statistics for a 24-hour period.

    Attributes:
        id: Unique summary identifier.
        date: Summary date.
        device_id: Device identifier.
        total_interactions: Count of all interactions.
        successful_interactions: Count of successful interactions.
        error_count: Count of failed interactions.
        avg_latency_ms: Average total latency.
        p95_latency_ms: 95th percentile latency.
        mode_breakdown: Count per mode.
        top_intents: Top intents with counts.
        action_items: Extracted action items.
        notable_interactions: Unusual or complex queries.
        generated_at: When summary was generated.
    """

    id: UUID
    date: date
    device_id: str
    total_interactions: int
    successful_interactions: int
    error_count: int
    avg_latency_ms: int
    p95_latency_ms: int
    mode_breakdown: dict[str, int]
    top_intents: list[dict[str, Any]]
    action_items: list[ActionItem]
    notable_interactions: list[dict[str, Any]]
    generated_at: datetime

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.total_interactions == 0:
            return 0.0
        return self.error_count / self.total_interactions

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary."""
        return {
            "id": str(self.id),
            "date": self.date.isoformat(),
            "device_id": self.device_id,
            "total_interactions": self.total_interactions,
            "successful_interactions": self.successful_interactions,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "mode_breakdown": self.mode_breakdown,
            "top_intents": self.top_intents,
            "action_items": [
                {"text": a.text, "source": a.source_transcript}
                for a in self.action_items
            ],
            "notable_interactions": self.notable_interactions,
            "generated_at": self.generated_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Convert summary to Markdown format."""
        lines = [
            f"# Daily Summary: {self.date.isoformat()}",
            "",
            f"**Device**: {self.device_id}",
            f"**Generated**: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            "",
            "## Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Interactions | {self.total_interactions} |",
            f"| Successful | {self.successful_interactions} |",
            f"| Errors | {self.error_count} |",
            f"| Error Rate | {self.error_rate:.1%} |",
            f"| Avg Latency | {self.avg_latency_ms}ms |",
            f"| P95 Latency | {self.p95_latency_ms}ms |",
            "",
        ]

        # Mode breakdown
        if self.mode_breakdown:
            lines.append("## Mode Breakdown")
            lines.append("")
            for mode, count in self.mode_breakdown.items():
                lines.append(f"- **{mode}**: {count}")
            lines.append("")

        # Top intents
        if self.top_intents:
            lines.append("## Top Intents")
            lines.append("")
            for intent_data in self.top_intents[:10]:
                intent = intent_data["intent"]
                count = intent_data["count"]
                lines.append(f"- **{intent}**: {count}")
            lines.append("")

        # Action items
        if self.action_items:
            lines.append("## Action Items")
            lines.append("")
            for item in self.action_items:
                lines.append(f"- [ ] {item.text}")
            lines.append("")

        return "\n".join(lines)


def extract_action_items(interactions: list[Interaction]) -> list[ActionItem]:
    """Extract action items from interactions.

    Looks for reminder and task-related intents.

    Args:
        interactions: List of interactions to process.

    Returns:
        List of extracted action items.
    """
    items = []

    for interaction in interactions:
        if interaction.intent == "reminder_set":
            # Extract the action from reminder
            message = interaction.entities.get("message", "")
            if not message:
                # Try to extract from transcript
                message = _extract_reminder_text(interaction.transcript)

            if message:
                items.append(
                    ActionItem(
                        text=message,
                        source_transcript=interaction.transcript,
                    )
                )

    return items


def _extract_reminder_text(transcript: str) -> str:
    """Extract reminder text from transcript.

    Args:
        transcript: The raw transcript.

    Returns:
        Extracted reminder text.
    """
    # Common patterns
    patterns = [
        r"remind me to (.+?)(?:\s+(?:in|at|tomorrow|on)\s|$)",
        r"don't forget to (.+?)(?:\s+(?:in|at|tomorrow|on)\s|$)",
        r"reminder to (.+?)(?:\s+(?:in|at|tomorrow|on)\s|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, transcript, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return ""


class SummaryGenerator:
    """Generates daily summaries from stored interactions."""

    def __init__(self, storage: InteractionStorage) -> None:
        """Initialize the summary generator.

        Args:
            storage: Storage instance to query.
        """
        self._storage = storage

    def generate(self, target_date: date, device_id: str) -> DailySummary:
        """Generate a daily summary.

        Args:
            target_date: Date to generate summary for.
            device_id: Device to generate summary for.

        Returns:
            Generated DailySummary.
        """
        # Get interactions for the date
        start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )
        end = datetime.combine(target_date, datetime.max.time()).replace(
            tzinfo=timezone.utc
        )

        interactions = self._storage.sqlite.get_by_date_range(start, end)

        # Filter by device
        interactions = [i for i in interactions if i.device_id == device_id]

        # Calculate statistics
        total = len(interactions)
        errors = sum(1 for i in interactions if i.error is not None)
        successful = total - errors

        # Latencies
        latencies = []
        for i in interactions:
            if "total" in i.latency_ms:
                latencies.append(i.latency_ms["total"])

        avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0
        p95_latency = self._calculate_percentile(latencies, 0.95)

        # Mode breakdown
        mode_breakdown: dict[str, int] = {}
        for i in interactions:
            mode = i.mode.value
            mode_breakdown[mode] = mode_breakdown.get(mode, 0) + 1

        # Top intents
        intent_counts: dict[str, int] = {}
        for i in interactions:
            intent_counts[i.intent] = intent_counts.get(i.intent, 0) + 1

        top_intents = sorted(
            [{"intent": k, "count": v} for k, v in intent_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )[:10]

        # Extract action items
        action_items = extract_action_items(interactions)

        return DailySummary(
            id=uuid.uuid4(),
            date=target_date,
            device_id=device_id,
            total_interactions=total,
            successful_interactions=successful,
            error_count=errors,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            mode_breakdown=mode_breakdown,
            top_intents=top_intents,
            action_items=action_items,
            notable_interactions=[],
            generated_at=datetime.now(timezone.utc),
        )

    def _calculate_percentile(self, values: list[int], percentile: float) -> int:
        """Calculate a percentile value.

        Args:
            values: List of values.
            percentile: Percentile to calculate (0.0-1.0).

        Returns:
            Percentile value.
        """
        if not values:
            return 0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        index = min(index, len(sorted_values) - 1)

        return sorted_values[index]

    def save_markdown(self, summary: DailySummary, output_path: Path) -> None:
        """Save summary as Markdown file.

        Args:
            summary: The summary to save.
            output_path: Path to write to.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary.to_markdown())


__all__ = [
    "ActionItem",
    "DailySummary",
    "SummaryGenerator",
    "extract_action_items",
]
