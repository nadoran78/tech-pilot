import sqlite3
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from tech_pilot.storage import NewsItem, SQLiteNewsRepository, StoreStatus, migrations
from tech_pilot.storage.migrations import Migration, apply_migrations


def make_item(**overrides: object) -> NewsItem:
    values: dict[str, object] = {
        "source_id": "openai-news",
        "external_id": "release-1",
        "canonical_url": "https://example.com/releases/1#summary",
        "title": "Release one",
        "published_at": datetime(2026, 9, 7, 9, 0, tzinfo=timezone(timedelta(hours=9))),
        "published_at_raw": "Sun, 07 Sep 2026 09:00:00 +0900",
        "collected_at": datetime(2026, 9, 7, 1, 0, tzinfo=UTC),
        "evidence_url": "https://example.com/releases/1",
        "source_endpoint": "https://example.com/feed.xml",
        "excerpt": "A short evidence-backed summary.",
        "raw_metadata": {"author": "Example"},
    }
    values.update(overrides)
    return NewsItem(**values)  # type: ignore[arg-type]


def test_migrations_are_applied_once(tmp_path: Path) -> None:
    database_path = tmp_path / "news.sqlite3"
    repository = SQLiteNewsRepository(database_path)

    repository.migrate()
    repository.migrate()

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'news_items'"
        ).fetchone()

    assert rows == [
        (1, "create_news_items"),
        (2, "create_source_http_validators"),
    ]
    assert table == ("news_items",)


def test_failed_migration_rolls_back_before_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "news.sqlite3"
    SQLiteNewsRepository(database_path).migrate()
    existing_migrations = migrations.MIGRATIONS
    failed_migration = Migration(
        version=3,
        name="create_retryable_table",
        statements=(
            "CREATE TABLE retryable_items (id INTEGER PRIMARY KEY)",
            "CREATE INDEX retryable_items_missing_column ON retryable_items(missing_column)",
        ),
    )
    completed_migration = Migration(
        version=3,
        name="create_retryable_table",
        statements=("CREATE TABLE retryable_items (id INTEGER PRIMARY KEY)",),
    )

    with sqlite3.connect(database_path) as connection:
        monkeypatch.setattr(migrations, "MIGRATIONS", (*existing_migrations, failed_migration))
        with pytest.raises(sqlite3.OperationalError):
            apply_migrations(connection)

        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'retryable_items'"
        ).fetchone()
        version = connection.execute(
            "SELECT version FROM schema_migrations WHERE version = 3"
        ).fetchone()

        assert table is None
        assert version is None

        monkeypatch.setattr(migrations, "MIGRATIONS", (*existing_migrations, completed_migration))
        apply_migrations(connection)

    with sqlite3.connect(database_path) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'retryable_items'"
        ).fetchone()
        version = connection.execute(
            "SELECT version FROM schema_migrations WHERE version = 3"
        ).fetchone()

    assert table == ("retryable_items",)
    assert version == (3,)


def test_stores_and_reads_all_news_item_fields(tmp_path: Path) -> None:
    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")

    result = repository.store(make_item())
    stored = repository.get(result.item_id) if result.item_id is not None else None

    assert result.status is StoreStatus.INSERTED
    assert stored is not None
    assert stored.item.canonical_url == "https://example.com/releases/1"
    assert stored.item.title == "Release one"
    assert stored.item.collected_at == datetime(2026, 9, 7, 1, 0, tzinfo=UTC)
    assert stored.item.published_at_raw == "Sun, 07 Sep 2026 09:00:00 +0900"
    assert stored.item.raw_metadata == {"author": "Example"}


def test_same_source_and_external_id_is_a_duplicate(tmp_path: Path) -> None:
    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    first = repository.store(make_item())
    duplicate = repository.store(
        make_item(canonical_url="https://example.com/releases/1-updated", title="Updated title")
    )

    assert duplicate.status is StoreStatus.DUPLICATE
    assert duplicate.item_id == first.item_id
    assert repository.count() == 1


def test_same_canonical_url_is_a_duplicate_without_external_id(tmp_path: Path) -> None:
    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    first = repository.store(make_item(external_id=None))
    duplicate = repository.store(make_item(source_id="another-source", external_id=None))

    assert duplicate.status is StoreStatus.DUPLICATE
    assert duplicate.item_id == first.item_id
    assert repository.count() == 1


def test_conflicting_technical_identities_require_review(tmp_path: Path) -> None:
    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    external_identity = repository.store(make_item())
    url_identity = repository.store(
        make_item(
            source_id="another-source",
            external_id="release-2",
            canonical_url="https://example.com/releases/2",
            evidence_url="https://example.com/releases/2",
        )
    )
    conflict = repository.store(
        make_item(
            canonical_url="https://example.com/releases/2",
            evidence_url="https://example.com/releases/2",
        )
    )

    assert external_identity.status is StoreStatus.INSERTED
    assert url_identity.status is StoreStatus.INSERTED
    assert conflict.status is StoreStatus.REVIEW_REQUIRED
    assert conflict.item_id is None
    assert repository.count() == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", " "),
        ("title", " "),
        ("canonical_url", "/relative"),
        ("evidence_url", "/relative"),
        ("source_endpoint", "/relative"),
    ],
)
def test_invalid_required_values_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValueError):
        make_item(**{field: value})
