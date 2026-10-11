import sqlite3
from io import StringIO
from pathlib import Path

import httpx
import pytest

from tech_pilot import cli
from tech_pilot.collection.coordinator import collect_sources
from tech_pilot.collection.models import CollectionStatus, CollectionSummary
from tech_pilot.collection.registry import APPROVED_SOURCES, SourceRegistration, SourceRegistry
from tech_pilot.storage import SQLiteNewsRepository
from tech_pilot.storage.history import SQLiteRunHistory


def fake_success(repository: SQLiteNewsRepository, client: httpx.Client) -> CollectionSummary:
    return CollectionSummary("test-source", CollectionStatus.COMPLETED, 200, inserted=0)


@pytest.mark.parametrize("source", ["", " ", " padded "])
def test_registry_rejects_invalid_ids(source: str) -> None:
    with pytest.raises(ValueError):
        SourceRegistry((SourceRegistration(source, fake_success),))


def test_registry_rejects_duplicate_ids() -> None:
    entry = SourceRegistration("test-source", fake_success)
    with pytest.raises(ValueError, match="duplicate"):
        SourceRegistry((entry, entry))


def test_registry_snapshots_input() -> None:
    entries = [SourceRegistration("test-source", fake_success)]
    registry = SourceRegistry(entries)
    entries.clear()
    assert registry.source_ids == ("test-source",)


def test_cli_executes_injected_registry_without_source_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = SourceRegistry((SourceRegistration("test-source", fake_success),))
    monkeypatch.setattr(cli, "APPROVED_SOURCES", registry)
    original_client = httpx.Client
    monkeypatch.setattr(
        cli.httpx,
        "Client",
        lambda: original_client(
            transport=httpx.MockTransport(lambda request: pytest.fail("HTTP sent"))
        ),
    )
    database = tmp_path / "news.sqlite3"
    output = StringIO()
    assert cli.main(["collect", "--database", str(database)], stdout=output) == 0
    assert "출처=test-source" in output.getvalue()
    assert SQLiteRunHistory(database).list_runs(1)[0].source_id == "test-source"


@pytest.mark.parametrize("mode", ["success", "exception", "mismatch"])
def test_fake_extension_uses_common_flow_and_history(tmp_path: Path, mode: str) -> None:
    calls: list[str] = []

    def extension(repository: SQLiteNewsRepository, client: httpx.Client) -> CollectionSummary:
        calls.append("test-source")
        if mode == "exception":
            raise sqlite3.OperationalError("private path")
        if mode == "mismatch":
            return CollectionSummary("wrong-source", CollectionStatus.COMPLETED, 200)
        return fake_success(repository, client)

    def following(repository: SQLiteNewsRepository, client: httpx.Client) -> CollectionSummary:
        calls.append("following-source")
        return CollectionSummary("following-source", CollectionStatus.UNCHANGED, 304)

    registry = SourceRegistry(
        (
            SourceRegistration("test-source", extension),
            SourceRegistration("following-source", following),
        )
    )
    database = tmp_path / "news.sqlite3"
    history = SQLiteRunHistory(database)
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("HTTP sent"))
    ) as client:
        results = collect_sources(
            SQLiteNewsRepository(database), client, history=history, registry=registry
        )
    assert calls == ["test-source", "following-source"]
    assert results[0].source_id == "test-source"
    assert results[0].status is (
        CollectionStatus.COMPLETED if mode == "success" else CollectionStatus.FAILED
    )
    assert results[1].status is CollectionStatus.UNCHANGED
    runs = history.list_runs(10)
    assert [run.source_id for run in runs] == ["following-source", "test-source"]
    assert all(run.finished_at is not None for run in runs)
    assert runs[1].status == results[0].status.value
    assert runs[1].error_code == (None if mode == "success" else "local_failed")
    assert APPROVED_SOURCES.source_ids == ("hugging-face-blog", "google-ai-blog")
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["collect", "--source", "test-source"])


def test_unknown_selection_rejected_before_any_side_effect(tmp_path: Path) -> None:
    database = tmp_path / "news.sqlite3"

    def should_not_run(repository: SQLiteNewsRepository, client: httpx.Client) -> CollectionSummary:
        pytest.fail("collector called before full selection validation")

    registry = SourceRegistry((SourceRegistration("test-source", should_not_run),))
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("HTTP sent"))
    ) as client:
        with pytest.raises(ValueError, match="unknown"):
            collect_sources(
                SQLiteNewsRepository(database),
                client,
                history=SQLiteRunHistory(database),
                registry=registry,
                source_ids=("test-source", "unknown"),
            )
    assert not database.exists()


def test_explicit_selection_order_and_deduplication(tmp_path: Path) -> None:
    calls: list[str] = []

    def make_collector(source: str):
        def collect(repository: SQLiteNewsRepository, client: httpx.Client) -> CollectionSummary:
            calls.append(source)
            return CollectionSummary(source, CollectionStatus.COMPLETED, 200)

        return collect

    registry = SourceRegistry(
        tuple(SourceRegistration(source, make_collector(source)) for source in ("first", "second"))
    )
    database = tmp_path / "news.sqlite3"
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: pytest.fail("HTTP sent"))
    ) as client:
        collect_sources(
            SQLiteNewsRepository(database),
            client,
            history=SQLiteRunHistory(database),
            registry=registry,
            source_ids=("second", "first", "second"),
        )
    assert calls == ["second", "first"]
    assert len(SQLiteRunHistory(database).list_runs(10)) == 2


@pytest.mark.parametrize("command", ["collect", "list", "history"])
def test_cli_choices_derive_from_registry(monkeypatch: pytest.MonkeyPatch, command: str) -> None:
    test_registry = SourceRegistry((SourceRegistration("test-source", fake_success),))
    monkeypatch.setattr(cli, "APPROVED_SOURCES", test_registry)
    assert (
        cli.build_parser().parse_args([command, "--source", "test-source"]).source == "test-source"
    )
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([command, "--source", "google-ai-blog"])
    assert APPROVED_SOURCES.source_ids == ("hugging-face-blog", "google-ai-blog")
