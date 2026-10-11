"""Persistent source-run lifecycle, independent from daily request reservations."""

from dataclasses import dataclass
from datetime import UTC, datetime

from tech_pilot.storage.migrations import apply_migrations
from tech_pilot.storage.repository import SQLiteNewsRepository


@dataclass(frozen=True, slots=True)
class CollectionRun:
    run_id: int
    source_id: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    http_status: int | None
    inserted: int | None
    duplicates: int | None
    review_required: int | None
    skipped: int | None
    error_code: str | None


class SQLiteRunHistory(SQLiteNewsRepository):
    """Store committed starts and single terminal updates in short transactions."""

    def start(self, source_id: str) -> int:
        if not source_id.strip():
            raise ValueError("source_id must not be blank")
        with self._connect() as connection:
            apply_migrations(connection)
            cursor = connection.execute(
                "INSERT INTO collection_runs(source_id, started_at, status) "
                "VALUES (?, ?, 'running')",
                (source_id, datetime.now(UTC).isoformat(timespec="microseconds")),
            )
            assert cursor.lastrowid is not None
            return cursor.lastrowid

    def finish(
        self,
        run_id: int,
        *,
        status: str,
        http_status: int | None,
        counts: tuple[int, int, int, int] | None,
        error_code: str | None,
    ) -> None:
        if status not in {"completed", "unchanged", "failed", "limit_reached"}:
            raise ValueError("invalid terminal status")
        if status == "failed":
            counts = None
        elif counts is None or any(value < 0 for value in counts):
            raise ValueError("terminal success requires nonnegative counts")
        if status in {"unchanged", "limit_reached"} and counts != (0, 0, 0, 0):
            raise ValueError("unprocessed runs require zero counts")
        if (status == "failed") != (error_code is not None):
            raise ValueError("only failed runs require an error code")
        values = counts if counts is not None else (None, None, None, None)
        with self._connect() as connection:
            apply_migrations(connection)
            cursor = connection.execute(
                """UPDATE collection_runs SET finished_at=?, status=?, http_status=?,
                inserted=?, duplicates=?, review_required=?, skipped=?, error_code=?
                WHERE run_id=? AND status='running'""",
                (
                    datetime.now(UTC).isoformat(timespec="microseconds"),
                    status,
                    http_status,
                    *values,
                    error_code,
                    run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise ValueError("run is missing or already finished")

    def list_runs(self, limit: int, *, source_id: str | None = None) -> tuple[CollectionRun, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            apply_migrations(connection)
            rows = connection.execute(
                """SELECT * FROM collection_runs WHERE (? IS NULL OR source_id=?)
                ORDER BY started_at DESC, run_id DESC LIMIT ?""",
                (source_id, source_id, limit),
            ).fetchall()
        return tuple(
            CollectionRun(
                run_id=row["run_id"],
                source_id=row["source_id"],
                started_at=datetime.fromisoformat(row["started_at"]),
                finished_at=datetime.fromisoformat(row["finished_at"])
                if row["finished_at"]
                else None,
                status=row["status"],
                http_status=row["http_status"],
                inserted=row["inserted"],
                duplicates=row["duplicates"],
                review_required=row["review_required"],
                skipped=row["skipped"],
                error_code=row["error_code"],
            )
            for row in rows
        )
