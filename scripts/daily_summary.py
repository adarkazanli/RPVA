#!/usr/bin/env python3
"""Generate daily summary for Ara Voice Assistant.

Generates a Markdown summary of interactions for a given date.

Usage:
    python scripts/daily_summary.py                    # Today's summary
    python scripts/daily_summary.py --date 2024-01-15  # Specific date
    python scripts/daily_summary.py --device pi4-kitchen  # Specific device
"""

import argparse
import sys
from datetime import date, datetime
from pathlib import Path


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate daily summary for Ara Voice Assistant"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to generate summary for (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="default",
        help="Device ID to generate summary for",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path.home() / ".ara" / "data" / "interactions.db",
        help="Path to interactions database",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path.home() / ".ara" / "data" / "logs",
        help="Path to JSONL log directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path. Defaults to summaries/<date>.md",
    )

    args = parser.parse_args()

    # Parse date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
            return 1
    else:
        target_date = date.today()

    # Add project to path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    from ara.logger.storage import InteractionStorage
    from ara.logger.summary import SummaryGenerator

    # Check if database exists
    if not args.db.exists():
        print(f"Error: Database not found at {args.db}")
        print("No interactions have been logged yet.")
        return 1

    # Create storage and generator
    storage = InteractionStorage(
        db_path=args.db,
        log_dir=args.log_dir,
    )

    generator = SummaryGenerator(storage)

    # Generate summary
    print(f"Generating summary for {target_date} (device: {args.device})...")

    summary = generator.generate(target_date, device_id=args.device)

    if summary.total_interactions == 0:
        print(f"No interactions found for {target_date}.")
        return 0

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        summaries_dir = Path.home() / ".ara" / "summaries"
        summaries_dir.mkdir(parents=True, exist_ok=True)
        output_path = summaries_dir / f"{target_date}.md"

    # Save summary
    generator.save_markdown(summary, output_path)

    # Print summary to console
    print()
    print(summary.to_markdown())
    print()
    print(f"Summary saved to: {output_path}")

    # Print key stats
    print()
    print("Key Statistics:")
    print(f"  Total interactions: {summary.total_interactions}")
    print(f"  Successful: {summary.successful_interactions}")
    print(f"  Errors: {summary.error_count}")
    print(f"  Average latency: {summary.avg_latency_ms}ms")
    print(f"  P95 latency: {summary.p95_latency_ms}ms")

    if summary.action_items:
        print()
        print("Action Items:")
        for item in summary.action_items:
            print(f"  - {item.text}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
