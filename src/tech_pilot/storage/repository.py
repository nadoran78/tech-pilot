"""SQLite persistence for normalized news items."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from tech_pilot.storage.migrations import apply_migrations
from tech_pilot.storage.models import (
    HttpValidators,
    NewsItem,
    StoredNewsItem,
    StoreResult,
    StoreStatus,
)


class SQLiteNewsRepository:
    """Persist news items while preserving the approved technical identity rules."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path

    def migrate(self) -> None:
        """Create or update the repository schema."""

        with self._connect() as connection:
            apply_migrations(connection)

    def store(self, item: NewsItem) -> StoreResult:
        """Store ``item`` or return its duplicate/review-required outcome."""

        with self._connect() as connection:
            apply_migrations(connection)
            external_match = self._find_external_id_match(connection, item)
            url_match = self._find_canonical_url_match(connection, item)

            if external_match is not None and url_match is not None and external_match != url_match:
                return StoreResult(
                    status=StoreStatus.REVIEW_REQUIRED,
                    item_id=None,
                    reason="external_id and canonical_url refer to different stored news items",
                )

            existing_id = external_match if external_match is not None else url_match
            if existing_id is not None:
                return StoreResult(
                    status=StoreStatus.DUPLICATE,
                    item_id=existing_id,
                    reason="technical identity already exists",
                )

            cursor = connection.execute(
                """
                INSERT INTO news_items (
                    source_id, external_id, canonical_url, title, published_at,
                    published_at_raw, collected_at, evidence_url, source_endpoint,
                    excerpt, raw_metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.source_id,
                    item.external_id,
                    item.canonical_url,
                    item.title,
                    _serialize_datetime(item.published_at, normalize_to_utc=False),
                    item.published_at_raw,
                    _serialize_datetime(item.collected_at, normalize_to_utc=True),
                    item.evidence_url,
                    item.source_endpoint,
                    item.excerpt,
                    _serialize_metadata(item.raw_metadata),
                    datetime.now(UTC).isoformat(),
                ),
            )
            return StoreResult(
                status=StoreStatus.INSERTED,
                item_id=cursor.lastrowid,
                reason="news item stored",
            )

    def get(self, item_id: int) -> StoredNewsItem | None:
        """Return a stored item by id, if it exists."""

        with self._connect() as connection:
            apply_migrations(connection)
            row = connection.execute(
                """
                SELECT id, source_id, external_id, canonical_url, title, published_at,
                       published_at_raw, collected_at, evidence_url, source_endpoint,
                       excerpt, raw_metadata_json
                FROM news_items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        return _stored_item_from_row(row) if row is not None else None

    def count(self) -> int:
        """Return the number of persisted news items."""

        with self._connect() as connection:
            apply_migrations(connection)
            row = connection.execute("SELECT COUNT(*) FROM news_items").fetchone()
        assert row is not None
        return int(row[0])

    def get_http_validators(self, source_id: str) -> HttpValidators | None:
        """Return the most recently stored HTTP validators for ``source_id``."""

        with self._connect() as connection:
            apply_migrations(connection)
            row = connection.execute(
                """
                SELECT etag, last_modified
                FROM source_http_validators
                WHERE source_id = ?
                """,
                (_require_source_id(source_id),),
            ).fetchone()
        if row is None:
            return None
        return HttpValidators(etag=row["etag"], last_modified=row["last_modified"])

    def save_http_validators(self, source_id: str, validators: HttpValidators) -> None:
        """Replace the HTTP validators for ``source_id`` or clear empty values."""

        normalized_source_id = _require_source_id(source_id)
        with self._connect() as connection:
            apply_migrations(connection)
            if not validators.has_values():
                connection.execute(
                    "DELETE FROM source_http_validators WHERE source_id = ?",
                    (normalized_source_id,),
                )
                return
            connection.execute(
                """
                INSERT INTO source_http_validators(source_id, etag, last_modified, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    etag = excluded.etag,
                    last_modified = excluded.last_modified,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_source_id,
                    validators.etag,
                    validators.last_modified,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _find_external_id_match(connection: sqlite3.Connection, item: NewsItem) -> int | None:
        if item.external_id is None:
            return None
        row = connection.execute(
            "SELECT id FROM news_items WHERE source_id = ? AND external_id = ?",
            (item.source_id, item.external_id),
        ).fetchone()
        return int(row[0]) if row is not None else None

    @staticmethod
    def _find_canonical_url_match(connection: sqlite3.Connection, item: NewsItem) -> int | None:
        row = connection.execute(
            "SELECT id FROM news_items WHERE canonical_url = ?", (item.canonical_url,)
        ).fetchone()
        return int(row[0]) if row is not None else None


def _serialize_datetime(value: datetime | None, *, normalize_to_utc: bool) -> str | None:
    if value is None:
        return None
    if normalize_to_utc:
        return value.astimezone(UTC).isoformat()
    return value.isoformat()


def _serialize_metadata(metadata: object | None) -> str | None:
    if metadata is None:
        return None
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True)


def _stored_item_from_row(row: sqlite3.Row) -> StoredNewsItem:
    raw_metadata = json.loads(row["raw_metadata_json"]) if row["raw_metadata_json"] else None
    item = NewsItem(
        source_id=row["source_id"],
        external_id=row["external_id"],
        canonical_url=row["canonical_url"],
        title=row["title"],
        published_at=_parse_datetime(row["published_at"]),
        published_at_raw=row["published_at_raw"],
        collected_at=_parse_required_datetime(row["collected_at"]),
        evidence_url=row["evidence_url"],
        source_endpoint=row["source_endpoint"],
        excerpt=row["excerpt"],
        raw_metadata=raw_metadata,
    )
    return StoredNewsItem(id=int(row["id"]), item=item)


def _parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


def _parse_required_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _require_source_id(value: str) -> str:
    source_id = value.strip()
    if not source_id:
        msg = "source_id must not be blank"
        raise ValueError(msg)
    return source_id
