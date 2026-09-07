"""Versioned SQL migrations for the local SQLite database."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS = (
    Migration(
        version=1,
        name="create_news_items",
        statements=(
            """
            CREATE TABLE news_items (
                id INTEGER PRIMARY KEY,
                source_id TEXT NOT NULL,
                external_id TEXT,
                canonical_url TEXT NOT NULL,
                title TEXT NOT NULL,
                published_at TEXT,
                published_at_raw TEXT,
                collected_at TEXT NOT NULL,
                evidence_url TEXT NOT NULL,
                source_endpoint TEXT NOT NULL,
                excerpt TEXT,
                raw_metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """,
            """
            CREATE UNIQUE INDEX news_items_source_external_id_unique
            ON news_items(source_id, external_id)
            WHERE external_id IS NOT NULL
            """,
            """
            CREATE UNIQUE INDEX news_items_canonical_url_unique
            ON news_items(canonical_url)
            """,
        ),
    ),
)


def apply_migrations(connection: sqlite3.Connection) -> None:
    """Apply each unapplied migration exactly once to ``connection``."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    applied_versions = {
        row[0] for row in connection.execute("SELECT version FROM schema_migrations")
    }

    for migration in MIGRATIONS:
        if migration.version in applied_versions:
            continue
        _apply_migration(connection, migration)


def _apply_migration(connection: sqlite3.Connection, migration: Migration) -> None:
    """Apply one migration atomically, including its version record."""

    savepoint = f"migration_{migration.version}"
    connection.execute(f"SAVEPOINT {savepoint}")
    try:
        for statement in migration.statements:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
            (migration.version, migration.name, datetime.now(UTC).isoformat()),
        )
    except sqlite3.DatabaseError:
        connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
        connection.execute(f"RELEASE SAVEPOINT {savepoint}")
        raise
    connection.execute(f"RELEASE SAVEPOINT {savepoint}")
