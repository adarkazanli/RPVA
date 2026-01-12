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

    # Check network status
    from .router.mode import NetworkMonitor, NetworkStatus

    network_monitor = NetworkMonitor()
    network_status = network_monitor.check_connectivity()
    mode_indicator = (
        "ONLINE" if network_status == NetworkStatus.ONLINE else "OFFLINE"
    )

    # Print startup banner
    print("\n" + "=" * 50)
    print("  Ara Voice Assistant")
    print("=" * 50)
    print(f"  Version: {__version__}")
    print(f"  Profile: {args.profile or detect_profile().value}")
    print(f"  Mode: {mode_indicator}")
    print(f"  Wake word: {config.wake_word.keyword}")
    print(f"  STT: {config.stt.model} ({config.stt.device})")
    print(f"  LLM: {config.llm.model}")
    print(f"  TTS: {config.tts.voice}")
    print("=" * 50 + "\n")

    logger.info(f"Network status: {network_status.value}")

    # Initialize orchestrator
    logger.info("Initializing voice assistant components...")

    try:
        from .router.orchestrator import Orchestrator

        # Use mocks if testing config is enabled
        use_mocks = config.testing.mock_audio_enabled

        orchestrator = Orchestrator.from_config(config, use_mocks=use_mocks)
        logger.info("Components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        print(f"\nError: Failed to initialize voice assistant: {e}")
        print("\nMake sure you have:")
        print("  1. Run setup: ./scripts/setup.sh")
        print("  2. Downloaded models: ./scripts/download_models.sh")
        print("  3. Started Ollama: ollama serve")
        print("  4. Pulled LLM model: ollama pull llama3.2:3b")
        return 1

    # Setup signal handlers for graceful shutdown
    shutdown_requested = False

    def signal_handler(signum: int, frame: object) -> None:
        nonlocal shutdown_requested
        if shutdown_requested:
            logger.warning("Force quit requested")
            sys.exit(1)
        shutdown_requested = True
        logger.info("Shutdown requested, cleaning up...")
        orchestrator.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start voice loop
    logger.info("Starting voice loop - say '%s' to activate", config.wake_word.keyword)
    print(f"\nListening for wake word '{config.wake_word.keyword}'...")
    print("Press Ctrl+C to stop.\n")

    try:
        orchestrator.start()

        # Wait for shutdown
        while not shutdown_requested:
            import time

            time.sleep(0.1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        orchestrator.stop()
        logger.info("Ara shut down gracefully")

    return 0


if __name__ == "__main__":
    sys.exit(main())
