import sqlite3
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import httpx
import pytest

from tech_pilot import cli
from tech_pilot.collection.coordinator import collect_sources
from tech_pilot.collection.models import CollectionStatus
from tech_pilot.storage import DailyRequestReservationStatus, SQLiteNewsRepository, migrations
from tech_pilot.storage.history import SQLiteRunHistory


@pytest.mark.parametrize("status", ["completed", "unchanged", "failed", "limit_reached"])
def test_committed_lifecycle_and_counts(tmp_path: Path, status: str) -> None:
    database = tmp_path / "news.sqlite3"
    history = SQLiteRunHistory(database)
    run_id = history.start("hugging-face-blog")
    started = SQLiteRunHistory(database).list_runs(1)[0]
    assert started.status == "running"
    assert started.finished_at is None
    assert started.inserted is None
    assert started.started_at.utcoffset() == UTC.utcoffset(None)
    counts = (2, 1, 3, 4) if status in {"completed", "failed"} else (0, 0, 0, 0)
    history.finish(
        run_id,
        status=status,
        http_status=200,
        counts=counts,
        error_code="local_failed" if status == "failed" else None,
    )
    finished = history.list_runs(1)[0]
    assert finished.status == status
    assert finished.finished_at is not None
    assert finished.finished_at >= started.started_at
    assert (finished.inserted, finished.duplicates, finished.review_required, finished.skipped) == (
        (None, None, None, None) if status == "failed" else counts
    )
    with pytest.raises(ValueError):
        history.finish(
            run_id, status="completed", http_status=200, counts=(0, 0, 0, 0), error_code=None
        )


def test_history_filter_order_and_incomplete_display(tmp_path: Path) -> None:
    database = tmp_path / "news.sqlite3"
    history = SQLiteRunHistory(database)
    first = history.start("hugging-face-blog")
    second = history.start("google-ai-blog")
    third = history.start("hugging-face-blog")
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE collection_runs SET started_at=?", (datetime.now(UTC).isoformat(),)
        )
    assert [run.run_id for run in history.list_runs(2)] == [third, second]
    assert [run.run_id for run in history.list_runs(2, source_id="hugging-face-blog")] == [
        third,
        first,
    ]
    output = StringIO()
    assert (
        cli.main(
            [
                "history",
                "--database",
                str(database),
                "--source",
                "hugging-face-blog",
                "--limit",
                "1",
            ],
            stdout=output,
        )
        == 0
    )
    assert "완료 기록 없음: 진행 중 또는 중단 가능" in output.getvalue()
    assert "+00:00" in output.getvalue()
    assert "google-ai-blog" not in output.getvalue()
    assert output.getvalue().count("실행 #") == 1


def test_missing_database_and_invalid_limit_do_not_create_database(tmp_path: Path) -> None:
    database = tmp_path / "absent.sqlite3"
    output = StringIO()
    assert cli.main(["history", "--database", str(database)], stdout=output) == 0
    assert "이력이 없습니다" in output.getvalue()
    with pytest.raises(SystemExit):
        cli.main(["history", "--database", str(database), "--limit", "0"])
    assert not database.exists()


def test_history_read_failure_is_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "news.sqlite3"
    SQLiteRunHistory(database).start("hugging-face-blog")

    def fail(*args: object, **kwargs: object) -> None:
        raise sqlite3.OperationalError("SECRET private database path")

    monkeypatch.setattr(SQLiteRunHistory, "list_runs", fail)
    output = StringIO()
    assert cli.main(["history", "--database", str(database)], stdout=output) == 1
    assert "history_read_failed" in output.getvalue()
    assert "SECRET" not in output.getvalue()


@pytest.mark.parametrize(
    "status,counts,code",
    [
        ("running", (0, 0, 0, 0), None),
        ("completed", (-1, 0, 0, 0), None),
        ("completed", None, None),
        ("unchanged", (1, 0, 0, 0), None),
        ("limit_reached", (0, 1, 0, 0), None),
        ("failed", None, None),
        ("completed", (0, 0, 0, 0), "local_failed"),
    ],
)
def test_invalid_finish_leaves_running(
    tmp_path: Path, status: str, counts: tuple[int, int, int, int] | None, code: str | None
) -> None:
    history = SQLiteRunHistory(tmp_path / "news.sqlite3")
    run_id = history.start("hugging-face-blog")
    with pytest.raises(ValueError):
        history.finish(run_id, status=status, http_status=None, counts=counts, error_code=code)
    assert history.list_runs(1)[0].status == "running"


def test_upgrade_preserves_existing_tables_without_reconstruction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "news.sqlite3"
    with monkeypatch.context() as patch:
        patch.setattr(migrations, "MIGRATIONS", migrations.MIGRATIONS[:3])
        SQLiteNewsRepository(database).reserve_daily_request(
            "google-ai-blog", requested_at=datetime.now(UTC)
        )
    with sqlite3.connect(database) as connection:
        before = {
            table: connection.execute(f"SELECT * FROM {table}").fetchall()
            for table in (
                "news_items",
                "source_http_validators",
                "source_daily_request_reservations",
            )
        }
    assert SQLiteRunHistory(database).list_runs(20) == ()
    with sqlite3.connect(database) as connection:
        for table, rows in before.items():
            assert connection.execute(f"SELECT * FROM {table}").fetchall() == rows


@pytest.mark.parametrize("failure", ["start", "finish"])
def test_history_failure_isolated_without_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    database = tmp_path / "news.sqlite3"
    history = SQLiteRunHistory(database)
    original = getattr(SQLiteRunHistory, failure)
    calls = 0

    def fail_first(self: SQLiteRunHistory, *args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise sqlite3.OperationalError("SECRET private path")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(SQLiteRunHistory, failure, fail_first)
    hosts: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        # A separate connection sees the committed start before the request.
        assert history.list_runs(1)[0].status == "running"
        if request.url.host == "huggingface.co":
            return httpx.Response(304)
        fixture = Path(__file__).parent / "fixtures" / "google_ai_blog_feed.xml"
        return httpx.Response(200, text=fixture.read_text())

    original_client = httpx.Client
    monkeypatch.setattr(
        cli.httpx, "Client", lambda: original_client(transport=httpx.MockTransport(respond))
    )
    output = StringIO()
    assert cli.main(["collect", "--database", str(database)], stdout=output) == 1
    assert calls == 2
    assert hosts == (["blog.google"] if failure == "start" else ["huggingface.co", "blog.google"])
    assert f"이력오류=history_{failure}_failed" in output.getvalue()
    assert "SECRET" not in output.getvalue()
    runs = history.list_runs(10)
    assert runs[0].status == "completed"
    if failure == "finish":
        assert runs[1].status == "running"
        assert "출처=hugging-face-blog, 상태=unchanged" in output.getvalue()
    else:
        assert len(runs) == 1


@pytest.mark.parametrize(
    "mode,code",
    [
        ("request", "request_failed"),
        ("http", "http_failed"),
        ("parse", "parse_failed"),
        ("local", "local_failed"),
    ],
)
def test_failure_codes_do_not_store_sensitive_details(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, code: str
) -> None:
    import tech_pilot.collection.coordinator as coordinator

    database = tmp_path / "news.sqlite3"
    history = SQLiteRunHistory(database)

    def respond(request: httpx.Request) -> httpx.Response:
        if mode == "request":
            raise httpx.ConnectError("SECRET", request=request)
        return httpx.Response(503 if mode == "http" else 200, text="SECRET broken feed")

    if mode == "local":

        def fail(*args: object) -> None:
            raise sqlite3.OperationalError("SECRET")

        monkeypatch.setattr(coordinator, "collect_hugging_face_blog", fail)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        results = collect_sources(
            SQLiteNewsRepository(database),
            client,
            history=history,
            source_ids=("hugging-face-blog",),
        )
    assert results[0].status is CollectionStatus.FAILED
    assert history.list_runs(1)[0].error_code == code
    assert history.list_runs(1)[0].inserted is None
    assert b"SECRET" not in database.read_bytes()


def test_daily_reservation_independent_of_history(tmp_path: Path) -> None:
    database = tmp_path / "news.sqlite3"
    repository = SQLiteNewsRepository(database)
    repository.reserve_daily_request("google-ai-blog", requested_at=datetime.now(UTC))
    history = SQLiteRunHistory(database)
    assert history.list_runs(20) == ()  # No reconstruction from older reservation state.
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("HTTP sent"))
    ) as client:
        results = collect_sources(
            repository, client, history=history, source_ids=("google-ai-blog",)
        )
    assert results[0].status is CollectionStatus.LIMIT_REACHED
    run = history.list_runs(1)[0]
    assert run.status == "limit_reached"
    assert run.inserted == 0
    assert run.http_status is None
    reservation = repository.reserve_daily_request("google-ai-blog", requested_at=datetime.now(UTC))
    assert reservation.status is DailyRequestReservationStatus.ALREADY_RESERVED
