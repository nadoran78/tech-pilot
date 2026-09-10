"""Command-line entry point for Tech Pilot."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

import httpx

from tech_pilot import __version__
from tech_pilot.collection import (
    CollectionSummary,
    HuggingFaceBlogFetcher,
    collect_hugging_face_blog,
)
from tech_pilot.storage import SQLiteNewsRepository

DEFAULT_DATABASE_PATH = Path("data/tech-pilot.sqlite3")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for manual news collection."""
    parser = argparse.ArgumentParser(
        prog="tech-pilot",
        description="Prepare Tech Pilot commands for AI technology news collection.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    collect_parser = subparsers.add_parser("collect", help="승인된 RSS 출처를 한 번 수집합니다.")
    collect_parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite 데이터베이스 경로 (기본값: data/tech-pilot.sqlite3)",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    """Run a manual collection command or validate the root CLI arguments."""

    args = build_parser().parse_args(argv)
    if args.command != "collect":
        return 0

    output = stdout if stdout is not None else sys.stdout
    with httpx.Client() as client:
        summary = collect_hugging_face_blog(
            SQLiteNewsRepository(args.database),
            HuggingFaceBlogFetcher(client),
        )
    _write_summary(output, summary)
    if summary.status.value == "failed":
        return 1
    return 0


def _write_summary(output: TextIO, summary: CollectionSummary) -> None:
    """Render a stable, human-readable result without exposing response bodies."""

    fields = [
        f"출처={summary.source_id}",
        f"상태={summary.status}",
        f"HTTP={summary.http_status if summary.http_status is not None else '-'}",
        f"신규={summary.inserted}",
        f"중복={summary.duplicates}",
        f"검토필요={summary.review_required}",
        f"제외={summary.skipped}",
    ]
    if summary.error is not None:
        fields.append(f"오류={summary.error}")
    print("수집 결과: " + ", ".join(fields), file=output)
