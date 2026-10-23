"""Command-line entry point for Tech Pilot."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import httpx

from tech_pilot import __version__
from tech_pilot.collection import (
    CollectionStatus,
    CollectionSummary,
)
from tech_pilot.collection.coordinator import collect_sources
from tech_pilot.collection.registry import APPROVED_SOURCES
from tech_pilot.storage import SQLiteNewsRepository
from tech_pilot.storage.history import SQLiteRunHistory
from tech_pilot.understanding.console import show_understanding_history, understand_one

DEFAULT_DATABASE_PATH = Path("data/tech-pilot.sqlite3")
DEFAULT_LIST_LIMIT = 20


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for manual news collection."""
    source_ids = APPROVED_SOURCES.source_ids
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
        "--source", choices=source_ids, help="수집할 출처 (생략하면 모든 승인 출처)"
    )
    collect_parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite 데이터베이스 경로 (기본값: data/tech-pilot.sqlite3)",
    )
    list_parser = subparsers.add_parser("list", help="저장된 뉴스 항목을 최신순으로 조회합니다.")
    list_parser.add_argument("--source", choices=source_ids, help="조회할 출처")
    list_parser.add_argument(
        "--collected-since",
        type=_aware_timestamp,
        help="이 시각부터 최초 저장된 항목 조회 (timezone 포함 ISO 8601)",
    )
    list_parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite 데이터베이스 경로 (기본값: data/tech-pilot.sqlite3)",
    )
    list_parser.add_argument(
        "--limit",
        type=_positive_int,
        default=DEFAULT_LIST_LIMIT,
        help=f"표시할 최대 항목 수 (기본값: {DEFAULT_LIST_LIMIT})",
    )
    history_parser = subparsers.add_parser("history", help="출처별 수집 실행 이력을 조회합니다.")
    history_parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE_PATH)
    history_parser.add_argument("--source", choices=source_ids)
    history_parser.add_argument("--limit", type=_positive_int, default=20)
    understand_parser = subparsers.add_parser(
        "understand", help="뉴스 한 건의 제목을 설명·분류합니다."
    )
    understand_parser.add_argument(
        "--news-id",
        type=_sqlite_positive_int,
        required=True,
        help="처리할 저장 뉴스 ID (양의 정수)",
    )
    understand_parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="SQLite 경로 (기본값: data/tech-pilot.sqlite3)",
    )
    understanding_history = subparsers.add_parser(
        "understanding-history", help="뉴스 한 건의 설명·분류 처리 이력을 조회합니다."
    )
    understanding_history.add_argument(
        "--news-id",
        type=_sqlite_positive_int,
        required=True,
        help="조회할 저장 뉴스 ID (양의 정수)",
    )
    understanding_history.add_argument(
        "--limit", type=_sqlite_positive_int, default=10, help="표시할 최대 이력 수 (기본값: 10)"
    )
    understanding_history.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE_PATH,
        help="읽기 전용 SQLite 경로 (기본값: data/tech-pilot.sqlite3)",
    )
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    """Run a manual collection command or validate the root CLI arguments."""

    args = build_parser().parse_args(argv)
    if args.command is None:
        return 0

    output = stdout if stdout is not None else sys.stdout
    if args.command == "understand":
        return understand_one(args.database, args.news_id, output)
    if args.command == "understanding-history":
        return show_understanding_history(args.database, args.news_id, args.limit, output)
    if args.command == "history":
        try:
            runs = (
                SQLiteRunHistory(args.database).list_runs(args.limit, source_id=args.source)
                if args.database.exists()
                else ()
            )
        except (sqlite3.Error, OSError, ValueError):
            print("수집 실행 이력 조회 실패: history_read_failed", file=output)
            return 1
        if not runs:
            print("수집 실행 이력이 없습니다.", file=output)
        for run in runs:
            note = (
                "완료 기록 없음: 진행 중 또는 중단 가능" if run.status == "running" else run.status
            )
            print(
                f"실행 #{run.run_id}: 출처={run.source_id}, 상태={note}, "
                f"시작={run.started_at.isoformat()}, "
                f"종료={run.finished_at.isoformat() if run.finished_at else '-'}, "
                f"HTTP={run.http_status}, 신규={run.inserted}, 중복={run.duplicates}, "
                f"검토필요={run.review_required}, 제외={run.skipped}, 오류코드={run.error_code}",
                file=output,
            )
        return 0
    if args.command == "list":
        _list_news_items(
            output,
            args.database,
            args.limit,
            source_id=args.source,
            collected_since=args.collected_since,
        )
        return 0

    with httpx.Client() as client:
        summaries = collect_sources(
            SQLiteNewsRepository(args.database),
            client,
            source_ids=(args.source,) if args.source else APPROVED_SOURCES.source_ids,
            history=SQLiteRunHistory(args.database),
            registry=APPROVED_SOURCES,
        )
    for summary in summaries:
        _write_summary(output, summary)
    return int(
        any(
            summary.status is CollectionStatus.FAILED or summary.history_error
            for summary in summaries
        )
    )


def _list_news_items(
    output: TextIO,
    database_path: Path,
    limit: int,
    *,
    source_id: str | None = None,
    collected_since: datetime | None = None,
) -> None:
    if not database_path.exists():
        print("저장된 뉴스 항목이 없습니다.", file=output)
        return

    items = SQLiteNewsRepository(database_path).list_recent(
        limit, source_id=source_id, collected_since=collected_since
    )
    if not items:
        print("저장된 뉴스 항목이 없습니다.", file=output)
        return

    for stored in items:
        item = stored.item
        published_at = item.published_at.isoformat() if item.published_at is not None else "-"
        print(
            "뉴스 "
            f"#{stored.id}: 제목={item.title}, 출처={item.source_id}, 원문={item.evidence_url}, "
            f"발표시각={published_at}, 수집시각={item.collected_at.isoformat()}",
            file=output,
        )


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
    if summary.history_error is not None:
        fields.append(f"이력오류={summary.history_error}")
    print("수집 결과: " + ", ".join(fields), file=output)


def _positive_int(value: str) -> int:
    try:
        integer = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("양의 정수를 입력해야 합니다.") from error
    if integer < 1:
        raise argparse.ArgumentTypeError("양의 정수를 입력해야 합니다.")
    return integer


def _sqlite_positive_int(value: str) -> int:
    integer = _positive_int(value)
    if integer > 2**63 - 1:
        raise argparse.ArgumentTypeError("SQLite 정수 범위의 양수를 입력하세요.")
    return integer


def _aware_timestamp(value: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.utcoffset() is None:
            raise ValueError("missing timezone")
        return timestamp.astimezone(UTC)
    except ValueError as error:
        raise argparse.ArgumentTypeError("timezone을 포함한 ISO 8601 시각을 입력하세요.") from error
