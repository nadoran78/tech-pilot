from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import httpx
import pytest

from tech_pilot import cli
from tech_pilot.collection import CollectionStatus, CollectionSummary, HuggingFaceBlogFetcher
from tech_pilot.collection.hugging_face_blog import collect_hugging_face_blog
from tech_pilot.sources import SOURCE_ID
from tech_pilot.storage import SQLiteNewsRepository

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hugging_face_blog_feed.xml"
COLLECTED_AT = datetime(2026, 9, 9, 1, 0, tzinfo=UTC)


def make_client(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)


def test_first_collection_stores_news_items_and_validators(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"] == "tech-pilot/0.1 (personal news collector)"
        assert "If-None-Match" not in request.headers
        return httpx.Response(
            200,
            text=FIXTURE_PATH.read_text(encoding="utf-8"),
            headers={"ETag": '"feed-v1"', "Last-Modified": "Tue, 09 Sep 2026 00:00:00 GMT"},
            request=request,
        )

    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    with make_client(httpx.MockTransport(handler)) as client:
        summary = collect_hugging_face_blog(
            repository,
            HuggingFaceBlogFetcher(client),
            collected_at=COLLECTED_AT,
        )

    assert summary == CollectionSummary(
        source_id=SOURCE_ID,
        status=CollectionStatus.COMPLETED,
        http_status=200,
        inserted=3,
        skipped=2,
    )
    assert repository.count() == 3
    assert repository.get_http_validators(SOURCE_ID) is not None
    assert repository.get_http_validators(SOURCE_ID).etag == '"feed-v1"'


def test_conditional_recollection_sends_validators_and_skips_304(tmp_path: Path) -> None:
    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        if request_count == 1:
            return httpx.Response(
                200,
                text=FIXTURE_PATH.read_text(encoding="utf-8"),
                headers={"ETag": '"feed-v1"', "Last-Modified": "Tue, 09 Sep 2026 00:00:00 GMT"},
                request=request,
            )
        assert request.headers["If-None-Match"] == '"feed-v1"'
        assert request.headers["If-Modified-Since"] == "Tue, 09 Sep 2026 00:00:00 GMT"
        return httpx.Response(304, request=request)

    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    with make_client(httpx.MockTransport(handler)) as client:
        fetcher = HuggingFaceBlogFetcher(client)
        first = collect_hugging_face_blog(repository, fetcher, collected_at=COLLECTED_AT)
        second = collect_hugging_face_blog(repository, fetcher, collected_at=COLLECTED_AT)

    assert first.inserted == 3
    assert second == CollectionSummary(
        source_id=SOURCE_ID,
        status=CollectionStatus.UNCHANGED,
        http_status=304,
    )
    assert repository.count() == 3


def test_http_failure_returns_a_safe_summary(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    with make_client(httpx.MockTransport(handler)) as client:
        summary = collect_hugging_face_blog(repository, HuggingFaceBlogFetcher(client))

    assert summary == CollectionSummary(
        source_id=SOURCE_ID,
        status=CollectionStatus.FAILED,
        http_status=503,
        error="HTTP 503",
    )
    assert repository.count() == 0


def test_collect_command_prints_a_human_readable_summary(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_collect(
        repository: SQLiteNewsRepository, fetcher: HuggingFaceBlogFetcher
    ) -> CollectionSummary:
        assert repository is not None
        assert fetcher is not None
        return CollectionSummary(
            source_id=SOURCE_ID,
            status=CollectionStatus.COMPLETED,
            http_status=200,
            inserted=2,
            duplicates=1,
            skipped=3,
        )

    monkeypatch.setattr(cli, "collect_hugging_face_blog", fake_collect)
    output = StringIO()

    exit_code = cli.main(
        ["collect", "--database", str(tmp_path / "news.sqlite3")],
        stdout=output,
    )

    assert exit_code == 0
    assert "출처=hugging-face-blog" in output.getvalue()
    assert "신규=2" in output.getvalue()
    assert "중복=1" in output.getvalue()
    assert "제외=3" in output.getvalue()
