import sqlite3
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import httpx
import pytest

from tech_pilot import cli
from tech_pilot.collection import CollectionStatus
from tech_pilot.collection.coordinator import collect_sources
from tech_pilot.storage import SQLiteNewsRepository
from tech_pilot.storage.history import SQLiteRunHistory

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("failed_host", [None, "huggingface.co", "blog.google"])
def test_sources_continue_after_http_failure(tmp_path: Path, failed_host: str | None) -> None:
    hosts: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        hosts.append(host)
        if host == failed_host:
            return httpx.Response(503)
        fixture = (
            "hugging_face_blog_feed.xml" if host == "huggingface.co" else "google_ai_blog_feed.xml"
        )
        return httpx.Response(200, text=(FIXTURES / fixture).read_text())

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        results = collect_sources(
            SQLiteNewsRepository(tmp_path / "news.sqlite3"),
            client,
            history=SQLiteRunHistory(tmp_path / "news.sqlite3"),
        )
    assert hosts == ["huggingface.co", "blog.google"]
    assert [result.status for result in results] == [
        CollectionStatus.FAILED if failed_host == host else CollectionStatus.COMPLETED
        for host in hosts
    ]


def test_google_limit_does_not_prevent_hugging_face(tmp_path: Path) -> None:
    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    repository.reserve_daily_request("google-ai-blog", requested_at=datetime.now(UTC))
    hosts: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        return httpx.Response(304)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        results = collect_sources(
            repository,
            client,
            source_ids=("google-ai-blog", "hugging-face-blog"),
            history=SQLiteRunHistory(tmp_path / "news.sqlite3"),
        )
    assert hosts == ["huggingface.co"]
    assert [result.status for result in results] == [
        CollectionStatus.LIMIT_REACHED,
        CollectionStatus.UNCHANGED,
    ]


def test_storage_failure_is_safe_and_does_not_stop_next_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tech_pilot.collection.coordinator as coordinator

    def fail(*args: object) -> None:
        raise sqlite3.OperationalError("private database path")

    monkeypatch.setattr(coordinator, "collect_hugging_face_blog", fail)
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, text=(FIXTURES / "google_ai_blog_feed.xml").read_text()
            )
        )
    ) as client:
        results = collect_sources(
            SQLiteNewsRepository(tmp_path / "news.sqlite3"),
            client,
            history=SQLiteRunHistory(tmp_path / "news.sqlite3"),
        )
    assert results[0].status is CollectionStatus.FAILED
    assert results[0].error == "Source collection failed"
    assert results[1].status is CollectionStatus.COMPLETED


@pytest.mark.parametrize("source", [None, "hugging-face-blog", "google-ai-blog"])
def test_cli_source_selection_and_summaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str | None
) -> None:
    original_client = httpx.Client
    hosts: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if request.url.host == "huggingface.co":
            return httpx.Response(503)
        return httpx.Response(200, text=(FIXTURES / "google_ai_blog_feed.xml").read_text())

    monkeypatch.setattr(
        cli.httpx, "Client", lambda: original_client(transport=httpx.MockTransport(respond))
    )
    args = ["collect", "--database", str(tmp_path / "news.sqlite3")]
    if source:
        args += ["--source", source]
    output = StringIO()
    code = cli.main(args, stdout=output)
    expected = (
        ["huggingface.co", "blog.google"]
        if source is None
        else ["huggingface.co" if source == "hugging-face-blog" else "blog.google"]
    )
    assert hosts == expected
    assert code == int("huggingface.co" in expected)
    assert output.getvalue().count("수집 결과:") == len(expected)


def test_unknown_source_is_rejected_before_network_or_database(tmp_path: Path) -> None:
    database = tmp_path / "news.sqlite3"
    with pytest.raises(SystemExit) as error:
        cli.main(["collect", "--source", "unknown", "--database", str(database)])
    assert error.value.code == 2
    assert not database.exists()
