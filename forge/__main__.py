"""Main entry point for running the self-referential forge.

Usage:
    python -m forge                         # Run with default config
    python -m forge --cycles 50             # Run 50 evolution cycles
    python -m forge --safety-off            # Disable safety checks
    python -m forge --human-approval        # Require human approval
    python -m forge --dashboard             # Launch dashboard alongside
    python -m forge --help                  # Show help
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys

from forge.orchestrator import EvolutionConfig, SelfReferentialOrchestrator


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the self-referential forge."""
    parser = argparse.ArgumentParser(
        description="Self-Referential Forge — evolve the forge's own components with genetic algorithms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m forge                    # Infinite self-referential evolution
  python -m forge --cycles 50        # 50 evolution cycles
  python -m forge --population 20    # Population of 20
  python -m forge --human-approval   # Require manual approval per mutation
  python -m forge --dashboard        # Launch real-time dashboard
        """,
    )
    parser.add_argument(
        "--cycles", type=int, default=-1,
        help="Number of evolution cycles (-1 = infinite, default: -1)",
    )
    parser.add_argument(
        "--population", type=int, default=30,
        help="Population size (default: 30)",
    )
    parser.add_argument(
        "--tournament", type=int, default=5,
        help="Tournament selection size (default: 5)",
    )
    parser.add_argument(
        "--mutation-rate", type=float, default=0.8,
        help="Mutation rate (default: 0.8)",
    )
    parser.add_argument(
        "--crossover-rate", type=float, default=0.2,
        help="Crossover rate (default: 0.2)",
    )
    parser.add_argument(
        "--parallel", type=int, default=2,
        help="Parallel generations (default: 2)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300,
        help="Sandbox timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "--safety-off", action="store_true",
        help="Disable safety validation",
    )
    parser.add_argument(
        "--human-approval", action="store_true",
        help="Require manual approval before applying mutations",
    )
    parser.add_argument(
        "--auto-commit", action="store_true",
        help="Auto-commit improvements to git",
    )
    parser.add_argument(
        "--dashboard", action="store_true",
        help="Launch the real-time dashboard alongside the forge",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Show version and exit",
    )
    return parser.parse_args(argv)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the self-referential forge."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def launch_dashboard() -> None:
    """Launch the FastAPI dashboard in a subprocess."""
    import subprocess
    dashboard_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "main.py")
    subprocess.Popen(
        [sys.executable, dashboard_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> int:
    """Main entry point. Returns exit code."""
    args = parse_args()

    if args.version:
        print("Self-Referential Forge v0.1.0")
        return 0

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    config = EvolutionConfig(
        population_size=args.population,
        tournament_size=args.tournament,
        mutation_rate=args.mutation_rate,
        crossover_rate=args.crossover_rate,
        parallel_generations=args.parallel,
        sandbox_timeout=args.timeout,
        safety_enabled=not args.safety_off,
        human_approval=args.human_approval,
        auto_commit=args.auto_commit,
        db_url=os.environ.get("FORGE_DB_URL", "sqlite:///self_referential_population.db"),
    )

    if args.dashboard:
        launch_dashboard()
        logger.info("Dashboard launched")

    orchestrator = SelfReferentialOrchestrator(config=config)

    try:
        asyncio.run(orchestrator.run(cycles=args.cycles))
    except KeyboardInterrupt:
        print("\nReceived interrupt, shutting down...")
        orchestrator.stop()
    except Exception as exc:
        logger.error("Fatal error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
