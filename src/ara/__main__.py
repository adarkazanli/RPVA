"""Ara Voice Assistant entry point.

Usage:
    python -m ara [OPTIONS]

Options:
    --config PATH    Path to YAML config file
    --profile NAME   Profile name (dev, prod)
    --help           Show this help message
    --version        Show version
"""

import argparse
import logging
import signal
import sys
from pathlib import Path

from . import __version__
from .config.loader import load_config
from .config.profiles import detect_profile, is_development


def setup_logging(level: str) -> None:
    """Configure logging based on config."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="ara",
        description="Ara Voice Assistant - Offline-first voice assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ara                     # Run with auto-detected profile
  python -m ara --profile dev       # Run with development profile
  python -m ara --profile prod      # Run with production profile
  python -m ara --config my.yaml    # Run with custom config file

Environment:
  ARA_PROFILE    Set profile (dev, prod, test)
""",
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to YAML config file",
        metavar="PATH",
    )

    parser.add_argument(
        "--profile",
        choices=["dev", "prod", "test"],
        help="Configuration profile to use",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"Ara Voice Assistant v{__version__}",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load config and exit (for testing)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point for Ara Voice Assistant.

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    args = parse_args()

    # Load configuration
    try:
        if args.config:
            config = load_config(path=args.config)
        elif args.profile:
            config = load_config(profile=args.profile)
        else:
            # Auto-detect profile
            profile = detect_profile()
            config = load_config(profile=profile.value)
    except FileNotFoundError as e:
        print(f"Error: Config file not found: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    # Setup logging
    setup_logging(config.logging.level)
    logger = logging.getLogger("ara")

    logger.info(f"Ara Voice Assistant v{__version__}")
    logger.info(f"Profile: {args.profile or detect_profile().value}")
    logger.info(f"Log level: {config.logging.level}")

    if args.dry_run:
        logger.info("Dry run mode - exiting after config load")
        logger.info(f"Wake word: {config.wake_word.keyword}")
        logger.info(f"STT model: {config.stt.model}")
        logger.info(f"LLM: {config.llm.provider}:{config.llm.model}")
        logger.info(f"TTS voice: {config.tts.voice}")
        return 0

    # Setup signal handlers for graceful shutdown
    shutdown_requested = False

    def signal_handler(signum: int, frame: object) -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            logger.warning("Force quit requested")
            sys.exit(1)
        shutdown_requested = True
        logger.info("Shutdown requested, cleaning up...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # TODO: Initialize components and start voice loop
    # This will be implemented in Phase 3 (US1)
    logger.info("Ara is starting up...")
    logger.warning("Voice loop not yet implemented - see Phase 3 tasks")

    # For now, just show config was loaded successfully
    print("\n" + "=" * 50)
    print("  Ara Voice Assistant")
    print("=" * 50)
    print(f"  Version: {__version__}")
    print(f"  Profile: {args.profile or detect_profile().value}")
    print(f"  Wake word: {config.wake_word.keyword}")
    print(f"  STT: {config.stt.model} ({config.stt.device})")
    print(f"  LLM: {config.llm.model}")
    print(f"  TTS: {config.tts.voice}")
    print("=" * 50)
    print("\n  Voice loop not yet implemented.")
    print("  Run setup first: ./scripts/setup.sh")
    print("  Then download models: ./scripts/download_models.sh")
    print("=" * 50 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
