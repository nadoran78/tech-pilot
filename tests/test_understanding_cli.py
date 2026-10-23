import json
import socket
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import httpx
import pytest

from tech_pilot.cli import main
from tech_pilot.storage import NewsItem, migrations
from tech_pilot.storage.understanding import SQLiteUnderstandingRepository
from tech_pilot.understanding import service
from tech_pilot.understanding.console import safe_text
from tech_pilot.understanding.models import ContentStatus, UnderstandingResult
from tech_pilot.understanding.rules import rule_request


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("understanding CLI must not create HTTP clients or open sockets")

    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def seed(path: Path) -> SQLiteUnderstandingRepository:
    repo = SQLiteUnderstandingRepository(path)
    repo.store(
        NewsItem(
            source_id="synthetic",
            title="Example model released?",
            canonical_url="https://example.com/item",
            evidence_url="https://example.com/item",
            collected_at=datetime.now(UTC),
            source_endpoint="https://example.com/rss",
        )
    )
    return repo


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "news #?.sqlite3"  # Exercise URI escaping on read-only connections.
    seed(path)
    return path


def run(command, database, *args):
    output = StringIO()
    code = main([command, "--news-id", "1", "--database", str(database), *args], stdout=output)
    return code, output.getvalue()


def test_understand_runs_once_then_reuses(database):
    code, output = run("understand", database)
    assert code == 0
    assert "새 처리" in output and "시도 #1" in output
    assert "완료(completed)" in output and "제목 기반 설명(described)" in output
    assert "기술·제품 동향" in output and "원문 미열람" in output
    assert "규칙 버전=rules-v4" in output and "처리 버전=2" in output
    code, output = run("understand", database)
    assert code == 0 and "재사용" in output
    assert len(SQLiteUnderstandingRepository(database).list_attempts(1)) == 1


def test_history_is_read_only_and_returns_current_result(database):
    run("understand", database)
    before = database.read_bytes(), database.stat().st_mtime_ns
    code, output = run("understanding-history", database)
    assert code == 0 and "현재 입력·버전" in output
    assert "model / released" in output and "Example model released?" in output
    assert (database.read_bytes(), database.stat().st_mtime_ns) == before


@pytest.mark.parametrize("command", ["understand", "understanding-history"])
def test_missing_database_is_not_created(tmp_path, command):
    path = tmp_path / "missing-parent" / "missing.sqlite3"
    code, output = run(command, path)
    assert code == (1 if command == "understand" else 0)
    assert ("원본" if command == "understand" else "이력이 없습니다") in output
    assert not path.parent.exists()


def test_history_on_v4_does_not_apply_migration(tmp_path, monkeypatch):
    path = tmp_path / "old.sqlite3"
    with monkeypatch.context() as patch:
        patch.setattr(migrations, "MIGRATIONS", migrations.MIGRATIONS[:4])
        seed(path)
    before = path.read_bytes()
    assert run("understanding-history", path)[0] == 0
    assert path.read_bytes() == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone() == (4,)
    # Only explicit processing applies the existing migration.
    assert run("understand", path)[0] == 0


def test_missing_original_is_rejected_without_writes(database):
    before = database.read_bytes()
    output = StringIO()
    assert main(["understand", "--news-id", "999", "--database", str(database)], stdout=output) == 1
    assert "understanding_input_rejected" in output.getvalue()
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "command,args",
    [
        ("understand", ["--news-id", "0"]),
        ("understand", ["--news-id", "-1"]),
        ("understand", ["--news-id", "x"]),
        ("understand", ["--news-id", str(2**63)]),
        ("understand", []),
        ("understanding-history", ["--news-id", "1", "--limit", "0"]),
        ("understanding-history", ["--news-id", "1", "--limit", "-2"]),
        ("understanding-history", ["--news-id", "1", "--limit", str(2**63)]),
    ],
)
def test_invalid_arguments_fail_before_database_access(tmp_path, command, args):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(SystemExit) as error:
        main([command, "--database", str(path), *args])
    assert error.value.code == 2 and not path.exists()


def test_insufficient_and_deferred_are_completed_not_execution_failures(database):
    repo = SQLiteUnderstandingRepository(database)
    with repo._connect() as connection:
        connection.execute("UPDATE news_items SET title='다음 장을 시작하며'")
    code, output = run("understand", database)
    assert code == 0 and "정보 부족(insufficient_information)" in output
    assert "실행=완료" in output and "설명=-" in output
    with repo._connect() as connection:
        connection.execute("UPDATE news_items SET title=?", ("model\nreleased",))
    code, output = run("understand", database)
    assert code == 0 and "보류(deferred)" in output
    assert "\\u000a" in output and "model\nreleased" not in output


def test_processing_failure_is_stored_and_has_failure_exit(database, monkeypatch):
    def broken(*args):
        raise RuntimeError("synthetic-secret-exception")

    monkeypatch.setattr(service, "apply_title_rules", broken)
    code, output = run("understand", database)
    assert code == 1 and "실행=실패(failed)" in output
    assert "processing_failed" in output and "결과 없음" in output
    assert "synthetic-secret" not in output
    assert run("understanding-history", database)[0] == 0


def test_save_failure_does_not_report_success(database):
    with sqlite3.connect(database) as connection:
        connection.execute("""CREATE TRIGGER deny_understanding BEFORE INSERT ON
            understanding_attempts BEGIN SELECT RAISE(ABORT, 'synthetic-secret'); END""")
    code, output = run("understand", database)
    assert code == 1 and "understanding_operation_failed" in output
    assert "처리 결과:" not in output and "synthetic-secret" not in output
    assert SQLiteUnderstandingRepository(database).list_attempts(1) == ()


@pytest.mark.parametrize("command", ["understand", "understanding-history"])
def test_corrupt_database_returns_safe_error(tmp_path, command):
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"synthetic invalid database")
    code, output = run(command, path)
    assert code == 1 and "실패" in output
    assert str(path) not in output and "synthetic invalid" not in output


def test_history_distinguishes_versions_inputs_and_missing_original(database):
    repo = SQLiteUnderstandingRepository(database)
    service.process_news(
        repo,
        1,
        replace(rule_request(), configuration_version="synthetic-old"),
        lambda *_: UnderstandingResult(ContentStatus.INSUFFICIENT, reason="synthetic old rules"),
    )
    run("understand", database)
    code, output = run("understanding-history", database)
    assert code == 0 and "현재 입력·버전" in output and "과거 입력·버전" in output
    assert output.index("시도 #2") < output.index("시도 #1")
    with repo._connect() as connection:
        connection.execute("UPDATE news_items SET title='Other news'")
    assert "현재 입력·버전" not in run("understanding-history", database)[1]
    with repo._connect() as connection:
        connection.execute("DELETE FROM news_items")
    assert "원본 없음(당시 입력)" in run("understanding-history", database)[1]


def test_limit_is_applied_in_sql_before_decode(database, monkeypatch):
    run("understand", database)
    repo = SQLiteUnderstandingRepository(database)
    for version in ("old-a", "old-b"):
        service.process_news(
            repo,
            1,
            replace(rule_request(), configuration_version=version),
            lambda *_: UnderstandingResult(ContentStatus.INSUFFICIENT, reason="synthetic"),
        )
    with repo._connect() as connection:
        connection.execute(
            "UPDATE understanding_attempts SET request_json='invalid json' WHERE id=1"
        )
    original_connect = sqlite3.connect
    queries = []

    def traced(database_uri, *args, **kwargs):
        assert "mode=ro" in database_uri and kwargs["uri"] is True
        connection = original_connect(database_uri, *args, **kwargs)
        connection.set_trace_callback(queries.append)
        return connection

    monkeypatch.setattr(sqlite3, "connect", traced)
    code, output = run("understanding-history", database, "--limit", "2")
    assert code == 0 and "시도 #1" not in output, (output, queries)
    assert output.count("시도 #") == 2
    assert any("LIMIT 2" in query for query in queries)
    assert not any("CREATE" in query or "UPDATE" in query for query in queries)


def test_result_controls_are_escaped_without_changing_storage(database):
    run("understand", database)
    with sqlite3.connect(database) as connection:
        row = connection.execute("SELECT result_json FROM understanding_attempts").fetchone()
        result = json.loads(row[0])
        result["text"] = "synthetic\x1b[31m\n\r\u202e\u2028"
        connection.execute("UPDATE understanding_attempts SET result_json=?", (json.dumps(result),))
    before = database.read_bytes()
    code, output = run("understanding-history", database)
    assert code == 0 and "\\u001b[31m\\u000a\\u000d\\u202e\\u2028" in output
    assert "\x1b" not in output and "\u202e" not in output
    assert database.read_bytes() == before
    assert safe_text("한글\t") == "한글\\u0009"


def test_understanding_does_not_change_collection_state(database):
    tables = (
        "news_items",
        "source_http_validators",
        "source_daily_request_reservations",
        "collection_runs",
    )

    def rows():
        with sqlite3.connect(database) as connection:
            return [connection.execute(f"SELECT * FROM {table}").fetchall() for table in tables]

    SQLiteUnderstandingRepository(database).reserve_daily_request(
        "synthetic", requested_at=datetime.now(UTC)
    )
    with sqlite3.connect(database) as connection:
        connection.execute("""INSERT INTO source_http_validators
            VALUES ('synthetic','synthetic-etag',NULL,'2026-10-23T00:00:00+00:00')""")
        connection.execute("""INSERT INTO collection_runs (source_id,started_at,status)
            VALUES ('synthetic','2026-10-23T00:00:00+00:00','running')""")
    before = rows()
    run("understand", database)
    run("understanding-history", database)
    assert rows() == before
