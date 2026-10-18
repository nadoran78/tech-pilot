import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tech_pilot.storage import NewsItem, migrations
from tech_pilot.storage.understanding import SQLiteUnderstandingRepository
from tech_pilot.understanding.models import (
    Category,
    ContentStatus,
    ErrorCode,
    ExecutionStatus,
    InputRejected,
    InputSnapshot,
    ProcessingRequest,
    RequestKind,
    UnderstandingResult,
    UnderstandingStorageError,
)
from tech_pilot.understanding.service import process_news


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteUnderstandingRepository:
    return make_repository(tmp_path)


def make_repository(tmp_path: Path) -> SQLiteUnderstandingRepository:
    repo = SQLiteUnderstandingRepository(tmp_path / "news.sqlite3")
    repo.store(
        NewsItem(
            source_id="synthetic",
            external_id="one",
            title="Example releases Widget",
            canonical_url="https://example.com/one",
            evidence_url="https://example.com/one",
            collected_at=datetime.now(UTC),
            source_endpoint="https://example.com/feed.xml",
        )
    )
    return repo


@pytest.fixture
def request_spec() -> ProcessingRequest:
    return ProcessingRequest(RequestKind.DESCRIBE, "fake", "1", "1")


def described(*_: object) -> UnderstandingResult:
    return UnderstandingResult(
        ContentStatus.DESCRIBED,
        Category.TECHNOLOGY,
        "제목에 Widget 발표가 표시됨",
        ("releases Widget",),
    )


def test_completed_result_is_persisted_and_reused(repository, request_spec):
    first = process_news(repository, 1, request_spec, described)

    def must_not_run(*_):
        pytest.fail("reuse must not execute processor")

    second = process_news(repository, 1, request_spec, must_not_run)
    assert not first.reused and second.reused
    assert first.attempt == second.attempt
    assert first.attempt.result == described()
    assert first.attempt.started_at <= first.attempt.finished_at
    assert first.attempt.finished_at.utcoffset().total_seconds() == 0
    assert len(repository.list_attempts(1)) == 1


@pytest.mark.parametrize("status", [ContentStatus.INSUFFICIENT, ContentStatus.DEFERRED])
def test_abstention_is_completed_and_reusable(repository, request_spec, status):
    result = UnderstandingResult(status, reason="本文未取得")
    first = process_news(repository, 1, request_spec, lambda *_: result)
    second = process_news(repository, 1, request_spec, described)
    assert first.attempt.status is ExecutionStatus.COMPLETED
    assert second.reused and second.attempt.result == result


def test_changed_identity_and_request_preserve_history(repository, request_spec):
    first = process_news(repository, 1, request_spec, described)
    for spec in (
        replace(request_spec, processing_version="2"),
        replace(request_spec, configuration_version="2"),
        replace(request_spec, method="other-fake"),
    ):
        assert not process_news(repository, 1, spec, described).reused
    summary = replace(request_spec, kind=RequestKind.SUMMARIZE)
    result = UnderstandingResult(ContentStatus.INSUFFICIENT, reason="원문 미열람")
    assert process_news(repository, 1, summary, lambda *_: result).attempt.result == result
    assert len(repository.list_attempts(1)) == 5
    assert repository.completed(first.attempt.reuse_key) == first.attempt


def test_changed_title_creates_new_snapshot(repository, request_spec, tmp_path):
    first = process_news(repository, 1, request_spec, described)
    with sqlite3.connect(tmp_path / "news.sqlite3") as connection:
        connection.execute("UPDATE news_items SET title=title || ' two' WHERE id=1")
    second = process_news(repository, 1, request_spec, described)
    assert not second.reused
    assert second.attempt.snapshot.fingerprint != first.attempt.snapshot.fingerprint
    assert repository.list_attempts(1)[1] == first.attempt


@pytest.mark.parametrize(
    "result",
    [
        UnderstandingResult(ContentStatus.SUMMARIZED, text="summary"),
        UnderstandingResult(ContentStatus.DESCRIBED, text="no evidence"),
        UnderstandingResult(ContentStatus.DESCRIBED, text="invented", evidence=("made up",)),
        UnderstandingResult(ContentStatus.INSUFFICIENT, text="forbidden", reason="missing"),
        UnderstandingResult(ContentStatus.DEFERRED),
        UnderstandingResult(
            ContentStatus.DESCRIBED, text="text", evidence=("Widget",), limitation=""
        ),
    ],
)
def test_invalid_result_is_safe_failure(repository, request_spec, result):
    outcome = process_news(repository, 1, request_spec, lambda *_: result)
    assert outcome.attempt.status is ExecutionStatus.FAILED
    assert outcome.attempt.error_code is ErrorCode.VALIDATION
    assert outcome.attempt.result is None


def test_summary_request_cannot_return_description(repository, request_spec):
    spec = replace(request_spec, kind=RequestKind.SUMMARIZE)
    assert process_news(repository, 1, spec, described).attempt.error_code is ErrorCode.VALIDATION


def test_processor_failure_is_not_retried_or_leaked(repository, request_spec, tmp_path):
    calls = []

    def broken(*_):
        calls.append(1)
        raise RuntimeError("synthetic-secret-do-not-store")

    failure = process_news(repository, 1, request_spec, broken)
    assert calls == [1]
    assert failure.attempt.error_code is ErrorCode.PROCESSING
    assert b"synthetic-secret-do-not-store" not in (tmp_path / "news.sqlite3").read_bytes()
    successful = process_news(repository, 1, request_spec, described)
    assert not successful.reused and successful.attempt.id != failure.attempt.id
    assert len(repository.list_attempts(1)) == 2


def test_missing_original_does_not_run_or_record(repository, request_spec):
    with pytest.raises(InputRejected):
        process_news(repository, 999, request_spec, lambda *_: pytest.fail("must not run"))
    assert repository.list_attempts(999) == ()


def test_stale_snapshot_is_rejected(repository, request_spec):
    stored = repository.get(1)
    snapshot = replace(InputSnapshot.from_news(stored), title="forged")
    with pytest.raises(InputRejected):
        repository.save_attempt(
            snapshot,
            request_spec,
            started_at=datetime.now(UTC),
            result=None,
            error_code=ErrorCode.PROCESSING,
        )
    assert repository.list_attempts(1) == ()


def test_storage_failure_does_not_report_success_or_retry(repository, request_spec, tmp_path):
    with sqlite3.connect(tmp_path / "news.sqlite3") as connection:
        connection.execute("""CREATE TRIGGER deny_understanding BEFORE INSERT ON
            understanding_attempts BEGIN SELECT RAISE(ABORT, 'synthetic-secret'); END""")
    calls = []

    def processor(*_):
        calls.append(1)
        return described()

    with pytest.raises(UnderstandingStorageError, match="^understanding_storage_failed$"):
        process_news(repository, 1, request_spec, processor)
    assert calls == [1] and repository.list_attempts(1) == ()
    assert repository.get(1).item.title == "Example releases Widget"


def test_processing_does_not_mutate_collection_tables(repository, request_spec, tmp_path):
    tables = (
        "news_items",
        "source_http_validators",
        "source_daily_request_reservations",
        "collection_runs",
    )
    repository.reserve_daily_request("synthetic", requested_at=datetime.now(UTC))
    with sqlite3.connect(tmp_path / "news.sqlite3") as connection:
        connection.execute("""INSERT INTO source_http_validators
            VALUES ('synthetic', 'example-etag', NULL, '2026-10-18T00:00:00+00:00')""")
        connection.execute("""INSERT INTO collection_runs
            (source_id,started_at,status) VALUES
            ('synthetic','2026-10-18T00:00:00+00:00','running')""")

    def snapshot():
        with sqlite3.connect(tmp_path / "news.sqlite3") as connection:
            return [connection.execute(f"SELECT * FROM {table}").fetchall() for table in tables]

    before = snapshot()
    process_news(repository, 1, request_spec, described)
    assert snapshot() == before


def test_supported_contract_versions_are_explicit():
    with pytest.raises(ValueError, match="unsupported contract"):
        ProcessingRequest(RequestKind.DESCRIBE, "fake", "1", "1", input_version="future")


@pytest.mark.parametrize("foreign_keys", [0, 1])
def test_upgrade_from_v4_preserves_original_and_reservation(tmp_path, monkeypatch, foreign_keys):
    all_migrations = migrations.MIGRATIONS
    with monkeypatch.context() as patch:
        patch.setattr(migrations, "MIGRATIONS", all_migrations[:4])
        repo = SQLiteUnderstandingRepository(tmp_path / "upgrade.sqlite3")
        repo.store(
            NewsItem(
                source_id="synthetic",
                title="Example releases Widget",
                canonical_url="https://example.com/upgrade",
                evidence_url="https://example.com/upgrade",
                source_endpoint="https://example.com/rss",
                collected_at=datetime.now(UTC),
            )
        )
        repo.reserve_daily_request("synthetic", requested_at=datetime.now(UTC))
        with sqlite3.connect(tmp_path / "upgrade.sqlite3") as connection:
            before_news = connection.execute("SELECT * FROM news_items").fetchall()
            before_reservations = connection.execute(
                "SELECT * FROM source_daily_request_reservations"
            ).fetchall()
    with sqlite3.connect(tmp_path / "upgrade.sqlite3") as connection:
        connection.execute(f"PRAGMA foreign_keys={foreign_keys}")
        migrations.apply_migrations(connection)
        migrations.apply_migrations(connection)
        assert (
            connection.execute("PRAGMA foreign_key_list(understanding_attempts)").fetchall() == []
        )
    with sqlite3.connect(tmp_path / "upgrade.sqlite3") as connection:
        assert connection.execute("SELECT * FROM news_items").fetchall() == before_news
        assert (
            connection.execute("SELECT * FROM source_daily_request_reservations").fetchall()
            == before_reservations
        )
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone() == (5,)
    assert (
        process_news(
            repo, 1, ProcessingRequest(RequestKind.DESCRIBE, "fake", "1", "1"), described
        ).attempt.status
        is ExecutionStatus.COMPLETED
    )


def test_identical_titles_do_not_share_results(repository, request_spec):
    original = repository.get(1).item
    second = repository.store(
        replace(
            original,
            external_id="two",
            canonical_url="https://example.com/two",
            evidence_url="https://example.com/two",
        )
    )
    first_result = process_news(repository, 1, request_spec, described)
    other_result = process_news(repository, second.item_id, request_spec, described)
    assert not other_result.reused
    assert first_result.attempt.reuse_key != other_result.attempt.reuse_key


def test_termination_does_not_claim_terminal_attempt(repository, request_spec):
    def terminate(*_):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        process_news(repository, 1, request_spec, terminate)
    assert repository.list_attempts(1) == ()


def test_completed_key_unique_constraint_is_retained(repository, request_spec):
    original = process_news(repository, 1, request_spec, described)
    snapshot = original.attempt.snapshot
    with pytest.raises(sqlite3.IntegrityError):
        repository.save_attempt(
            snapshot,
            request_spec,
            started_at=datetime.now(UTC),
            result=described(),
            error_code=None,
        )


def test_new_schema_has_no_fk_but_retains_local_constraints(repository, tmp_path):
    with sqlite3.connect(tmp_path / "news.sqlite3") as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert (
            connection.execute("PRAGMA foreign_key_list(understanding_attempts)").fetchall() == []
        )
        # Direct SQL bypasses application reference validation; other constraints still hold.
        connection.execute("""INSERT INTO understanding_attempts
            (news_id,reuse_key,snapshot_json,request_json,started_at,finished_at,status,error_code)
            VALUES (999,'synthetic-key','{}','{}','start','finish','failed','processing_failed')""")
        for update in ("news_id=NULL", "status='invalid'", "result_json='{}'"):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(f"UPDATE understanding_attempts SET {update}")


def test_save_rejects_missing_original_without_db_fk(repository, request_spec):
    snapshot = replace(InputSnapshot.from_news(repository.get(1)), news_id=999)
    with pytest.raises(InputRejected):
        repository.save_attempt(
            snapshot,
            request_spec,
            started_at=datetime.now(UTC),
            result=described(),
            error_code=None,
        )
    assert repository.list_attempts(999) == ()


def test_original_deleted_during_processing_is_rejected(repository, request_spec, tmp_path):
    def delete_original(*_):
        with sqlite3.connect(tmp_path / "news.sqlite3") as connection:
            connection.execute("DELETE FROM news_items WHERE id=1")
        return described()

    with pytest.raises(InputRejected):
        process_news(repository, 1, request_spec, delete_original)
    assert repository.list_attempts(1) == ()


def test_migration_5_failure_rolls_back_table_and_index(tmp_path, monkeypatch, request_spec):
    all_migrations = migrations.MIGRATIONS
    with monkeypatch.context() as patch:
        patch.setattr(migrations, "MIGRATIONS", all_migrations[:4])
        repo = make_repository(tmp_path)
    path = tmp_path / "news.sqlite3"
    broken = replace(
        all_migrations[-1],
        statements=(*all_migrations[-1].statements, "SELECT missing_column FROM news_items"),
    )
    with monkeypatch.context() as patch:
        patch.setattr(migrations, "MIGRATIONS", (*all_migrations[:-1], broken))
        with sqlite3.connect(path) as connection:
            with pytest.raises(sqlite3.OperationalError):
                migrations.apply_migrations(connection)
            assert (
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='understanding_attempts'"
                ).fetchone()
                is None
            )
            assert (
                connection.execute(
                    "SELECT version FROM schema_migrations WHERE version=5"
                ).fetchone()
                is None
            )
            assert (
                connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='understanding_completed_key'"
                ).fetchone()
                is None
            )
            assert connection.execute("SELECT COUNT(*) FROM news_items").fetchone() == (1,)
    repo.migrate()
    original = process_news(repo, 1, request_spec, described)
    assert repo.completed(original.attempt.reuse_key) == original.attempt
