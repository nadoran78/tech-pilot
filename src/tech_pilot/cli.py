"""Command-line entry point for Tech Pilot."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from tech_pilot import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the minimal CLI parser without starting collection work."""
    parser = argparse.ArgumentParser(
        prog="tech-pilot",
        description="Prepare Tech Pilot commands for AI technology news collection.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate CLI arguments and return successfully for the bootstrap command."""
    build_parser().parse_args(argv)
    return 0
