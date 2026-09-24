"""Tests for the bootstrap command-line interface."""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from tech_pilot.cli import build_parser, main
from tech_pilot.storage import NewsItem, SQLiteNewsRepository


def test_parser_describes_bootstrap_cli() -> None:
    parser = build_parser()

    assert parser.prog == "tech-pilot"
    assert "AI technology news collection" in parser.format_help()


def test_main_accepts_no_arguments() -> None:
    assert main([]) == 0


def test_list_command_prints_recent_stored_items(tmp_path: Path) -> None:
    database_path = tmp_path / "news.sqlite3"
    repository = SQLiteNewsRepository(database_path)
    repository.store(
        NewsItem(
            source_id="hugging-face-blog",
            external_id="older",
            canonical_url="https://huggingface.co/blog/older",
            title="Older post",
            collected_at=datetime(2026, 9, 10, 1, 0, tzinfo=UTC),
            evidence_url="https://huggingface.co/blog/older",
            source_endpoint="https://huggingface.co/blog/feed.xml",
        )
    )
    repository.store(
        NewsItem(
            source_id="hugging-face-blog",
            external_id="newer",
            canonical_url="https://huggingface.co/blog/newer",
            title="Newer post",
            published_at=datetime(2026, 9, 11, 9, 0, tzinfo=UTC),
            collected_at=datetime(2026, 9, 11, 1, 0, tzinfo=UTC),
            evidence_url="https://huggingface.co/blog/newer",
            source_endpoint="https://huggingface.co/blog/feed.xml",
        )
    )
    output = StringIO()

    exit_code = main(["list", "--database", str(database_path), "--limit", "1"], stdout=output)

    assert exit_code == 0
    assert "제목=Newer post" in output.getvalue()
    assert "제목=Older post" not in output.getvalue()
    assert "출처=hugging-face-blog" in output.getvalue()
    assert "원문=https://huggingface.co/blog/newer" in output.getvalue()
    assert "발표시각=2026-09-11T09:00:00+00:00" in output.getvalue()
    assert "수집시각=2026-09-11T01:00:00+00:00" in output.getvalue()


def test_list_command_marks_a_missing_published_time(tmp_path: Path) -> None:
    database_path = tmp_path / "news.sqlite3"
    SQLiteNewsRepository(database_path).store(
        NewsItem(
            source_id="hugging-face-blog",
            canonical_url="https://huggingface.co/blog/no-date",
            title="Post without a published time",
            collected_at=datetime(2026, 9, 11, 1, 0, tzinfo=UTC),
            evidence_url="https://huggingface.co/blog/no-date",
            source_endpoint="https://huggingface.co/blog/feed.xml",
        )
    )
    output = StringIO()

    exit_code = main(["list", "--database", str(database_path)], stdout=output)

    assert exit_code == 0
    assert "발표시각=-" in output.getvalue()


def test_list_command_handles_an_empty_existing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "news.sqlite3"
    SQLiteNewsRepository(database_path).migrate()
    output = StringIO()

    exit_code = main(["list", "--database", str(database_path)], stdout=output)

    assert exit_code == 0
    assert output.getvalue() == "저장된 뉴스 항목이 없습니다.\n"


def test_list_command_handles_a_missing_database_without_creating_it(tmp_path: Path) -> None:
    database_path = tmp_path / "missing.sqlite3"
    output = StringIO()

    exit_code = main(["list", "--database", str(database_path)], stdout=output)

    assert exit_code == 0
    assert output.getvalue() == "저장된 뉴스 항목이 없습니다.\n"
    assert not database_path.exists()
