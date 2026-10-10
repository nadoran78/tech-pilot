from datetime import UTC, datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import pytest

from tech_pilot import cli
from tech_pilot.storage import NewsItem, SQLiteNewsRepository

SINCE = datetime(2026, 10, 10, 5, tzinfo=UTC)


def populate(database: Path) -> SQLiteNewsRepository:
    repository = SQLiteNewsRepository(database)
    for index, (source, offset) in enumerate(
        [
            ("google-ai-blog", -1),
            ("google-ai-blog", 0),
            ("google-ai-blog", 1),
            ("hugging-face-blog", 1),
        ]
    ):
        repository.store(
            NewsItem(
                source_id=source,
                title=f"item-{index}",
                canonical_url=f"https://example.com/{index}",
                evidence_url=f"https://example.com/{index}",
                source_endpoint="https://example.com/feed",
                collected_at=SINCE + timedelta(seconds=offset),
                published_at=SINCE + timedelta(days=index),
            )
        )
    return repository


def test_repository_filters_before_sort_and_limit(tmp_path: Path) -> None:
    repository = populate(tmp_path / "news.sqlite3")
    assert [row.item.title for row in repository.list_recent(20, source_id="google-ai-blog")] == [
        "item-2",
        "item-1",
        "item-0",
    ]
    assert len(repository.list_recent(20, collected_since=SINCE)) == 3
    kst = SINCE.astimezone(timezone(timedelta(hours=9)))
    assert [
        row.item.title
        for row in repository.list_recent(20, source_id="google-ai-blog", collected_since=kst)
    ] == ["item-2", "item-1"]
    assert [
        row.item.title
        for row in repository.list_recent(1, source_id="google-ai-blog", collected_since=kst)
    ] == ["item-2"]
    assert repository.list_recent(20, collected_since=SINCE + timedelta(days=1)) == ()


def test_repository_rejects_naive_filter_time(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        SQLiteNewsRepository(tmp_path / "news.sqlite3").list_recent(
            20, collected_since=datetime(2026, 10, 10)
        )


def test_cli_filters_and_empty_result(tmp_path: Path) -> None:
    database = tmp_path / "news.sqlite3"
    populate(database)
    output = StringIO()
    assert (
        cli.main(
            [
                "list",
                "--database",
                str(database),
                "--source",
                "google-ai-blog",
                "--collected-since",
                "2026-10-10T14:00:00+09:00",
            ],
            stdout=output,
        )
        == 0
    )
    assert "item-2" in output.getvalue()
    assert "item-1" in output.getvalue()
    assert "item-0" not in output.getvalue()
    assert "item-3" not in output.getvalue()
    output = StringIO()
    cli.main(
        ["list", "--database", str(database), "--collected-since", "2027-01-01T00:00:00Z"],
        stdout=output,
    )
    assert output.getvalue().strip() == "저장된 뉴스 항목이 없습니다."


@pytest.mark.parametrize("timestamp", ["invalid", "2026-10-10", "2026-10-10T14:00:00"])
def test_cli_rejects_invalid_time_before_creating_database(tmp_path: Path, timestamp: str) -> None:
    database = tmp_path / "news.sqlite3"
    with pytest.raises(SystemExit) as error:
        cli.main(["list", "--database", str(database), "--collected-since", timestamp])
    assert error.value.code == 2
    assert not database.exists()
