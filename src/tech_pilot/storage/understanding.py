"""Append-only understanding attempts, isolated from news and collection state."""

import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import UTC, datetime

from tech_pilot.storage.migrations import apply_migrations
from tech_pilot.storage.repository import SQLiteNewsRepository, _stored_item_from_row
from tech_pilot.understanding.models import (
    Category,
    ContentStatus,
    ErrorCode,
    ExecutionStatus,
    InputRejected,
    InputSnapshot,
    ProcessingRequest,
    RequestKind,
    StoredAttempt,
    UnderstandingResult,
    canonical_json,
)


class SQLiteUnderstandingRepository(SQLiteNewsRepository):
    """One manual processor at a time; completed results are reused by exact key."""

    def read_history(
        self, news_id: int, *, limit: int = 10
    ) -> tuple[InputSnapshot | None, tuple[StoredAttempt, ...]]:
        """Read one consistent snapshot without creating a DB or applying migrations."""
        if (
            type(news_id) is not int
            or not 1 <= news_id <= 2**63 - 1
            or type(limit) is not int
            or not 1 <= limit <= 2**63 - 1
        ):
            raise ValueError("positive news id and limit required")
        if not self._database_path.exists():
            return None, ()
        uri = self._database_path.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("BEGIN")
            original = connection.execute(
                "SELECT * FROM news_items WHERE id=?", (news_id,)
            ).fetchone()
            snapshot = (
                InputSnapshot.from_news(_stored_item_from_row(original)) if original else None
            )
            has_attempts = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='understanding_attempts'"
            ).fetchone()
            if not has_attempts:
                return snapshot, ()
            rows = connection.execute(
                "SELECT * FROM understanding_attempts WHERE news_id=? ORDER BY id DESC LIMIT ?",
                (news_id, limit),
            ).fetchall()
            return snapshot, tuple(_decode(row) for row in rows)

    def completed(self, key: str) -> StoredAttempt | None:
        with self._connect() as connection:
            apply_migrations(connection)
            row = connection.execute(
                "SELECT * FROM understanding_attempts WHERE reuse_key=? AND status='completed'",
                (key,),
            ).fetchone()
        return _decode(row) if row is not None else None

    def list_attempts(self, news_id: int) -> tuple[StoredAttempt, ...]:
        with self._connect() as connection:
            apply_migrations(connection)
            rows = connection.execute(
                "SELECT * FROM understanding_attempts WHERE news_id=? ORDER BY id DESC", (news_id,)
            ).fetchall()
        return tuple(_decode(row) for row in rows)

    def save_attempt(
        self,
        snapshot: InputSnapshot,
        request: ProcessingRequest,
        *,
        started_at: datetime,
        result: UnderstandingResult | None,
        error_code: ErrorCode | None,
    ) -> StoredAttempt:
        if started_at.utcoffset() is None:
            raise ValueError("timezone required")
        if (result is None) == (error_code is None):
            raise ValueError("requires exactly one result or error")
        if error_code is not None and not isinstance(error_code, ErrorCode):
            raise ValueError("invalid error code")
        if result is not None:
            result.validate(snapshot, request)
        finished_at = datetime.now(UTC)
        if started_at > finished_at:
            raise ValueError("start cannot be after finish")
        with self._connect() as connection:
            apply_migrations(connection)
            connection.execute("BEGIN IMMEDIATE")
            original = connection.execute(
                "SELECT * FROM news_items WHERE id=?", (snapshot.news_id,)
            ).fetchone()
            if (
                original is None
                or InputSnapshot.from_news(_stored_item_from_row(original)) != snapshot
            ):
                raise InputRejected("original reference is missing or changed")
            cursor = connection.execute(
                """INSERT INTO understanding_attempts
                (news_id,reuse_key,snapshot_json,request_json,started_at,finished_at,
                 status,result_json,error_code) VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    snapshot.news_id,
                    request.reuse_key(snapshot),
                    canonical_json(asdict(snapshot)),
                    canonical_json(asdict(request)),
                    started_at.astimezone(UTC).isoformat(),
                    finished_at.isoformat(),
                    "completed" if result is not None else "failed",
                    canonical_json(asdict(result)) if result is not None else None,
                    error_code,
                ),
            )
            row = connection.execute(
                "SELECT * FROM understanding_attempts WHERE id=?", (cursor.lastrowid,)
            ).fetchone()
            assert row is not None
            attempt = _decode(row)
        return attempt  # The context has committed before reporting persistence.


def _decode(row: sqlite3.Row) -> StoredAttempt:
    raw_request = json.loads(row["request_json"])
    raw_request["kind"] = RequestKind(raw_request["kind"])
    raw_result = json.loads(row["result_json"]) if row["result_json"] is not None else None
    if raw_result is not None:
        raw_result["status"] = ContentStatus(raw_result["status"])
        raw_result["category"] = Category(raw_result["category"])
        raw_result["evidence"] = tuple(raw_result["evidence"])
    return StoredAttempt(
        id=row["id"],
        reuse_key=row["reuse_key"],
        snapshot=InputSnapshot(**json.loads(row["snapshot_json"])),
        request=ProcessingRequest(**raw_request),
        started_at=datetime.fromisoformat(row["started_at"]),
        finished_at=datetime.fromisoformat(row["finished_at"]),
        status=ExecutionStatus(row["status"]),
        result=UnderstandingResult(**raw_result) if raw_result is not None else None,
        error_code=ErrorCode(row["error_code"]) if row["error_code"] is not None else None,
    )
