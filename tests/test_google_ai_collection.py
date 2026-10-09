from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import httpx
import pytest

from tech_pilot.collection import CollectionStatus, GoogleAiBlogFetcher, collect_google_ai_blog
from tech_pilot.sources.google_ai_blog import SOURCE_ENDPOINT, SOURCE_ID
from tech_pilot.storage import SQLiteNewsRepository

FIXTURE = Path(__file__).parent / "fixtures" / "google_ai_blog_feed.xml"
NOW = datetime(2026, 10, 9, 1, tzinfo=UTC)


def test_success_limit_and_next_day_duplicate_collection(tmp_path: Path) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url) == SOURCE_ENDPOINT
        assert request.method == "GET"
        assert request.headers["User-Agent"] == "tech-pilot/0.1 (personal news collector)"
        assert "If-None-Match" not in request.headers
        assert "If-Modified-Since" not in request.headers
        assert request.extensions["timeout"]["read"] == 10.0
        return httpx.Response(200, text=FIXTURE.read_text(), headers={"ETag": "ignored"})

    repository = SQLiteNewsRepository(tmp_path / "news.sqlite3")
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        fetcher = GoogleAiBlogFetcher(client)
        first = collect_google_ai_blog(repository, fetcher, requested_at=NOW)
        limited = collect_google_ai_blog(repository, fetcher, requested_at=NOW)
        next_day = collect_google_ai_blog(repository, fetcher, requested_at=NOW + timedelta(days=1))
    assert first.status is CollectionStatus.COMPLETED
    assert first.inserted == 2
    assert first.skipped == 3
    assert limited.status is CollectionStatus.LIMIT_REACHED
    assert limited.http_status is None
    assert next_day.duplicates == 2
    assert len(requests) == 2
    assert repository.count() == 2
    assert repository.get_http_validators(SOURCE_ID) is None


@pytest.mark.parametrize("failure", ["timeout", "http", "xml", "redirect"])
def test_failures_retain_reservation_and_store_no_news(tmp_path: Path, failure: str) -> None:
    calls = 0

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if failure == "timeout":
            raise httpx.ReadTimeout("private response must not leak", request=request)
        if failure == "http":
            return httpx.Response(503)
        if failure == "redirect":
            return httpx.Response(301, headers={"Location": "https://example.com/other"})
        return httpx.Response(200, text="<rss><channel>")

    database = tmp_path / "news.sqlite3"
    with httpx.Client(transport=httpx.MockTransport(respond), follow_redirects=True) as client:
        first = collect_google_ai_blog(
            SQLiteNewsRepository(database), GoogleAiBlogFetcher(client), requested_at=NOW
        )
        second = collect_google_ai_blog(
            SQLiteNewsRepository(database), GoogleAiBlogFetcher(client), requested_at=NOW
        )
    assert first.status is CollectionStatus.FAILED
    assert "private" not in (first.error or "")
    assert second.status is CollectionStatus.LIMIT_REACHED
    assert calls == 1
    assert SQLiteNewsRepository(database).count() == 0


def test_concurrent_collectors_send_only_one_http_request(tmp_path: Path) -> None:
    database = tmp_path / "news.sqlite3"
    SQLiteNewsRepository(database).migrate()
    start = Barrier(2)
    calls: list[httpx.Request] = []

    def collect() -> CollectionStatus:
        start.wait(timeout=5)

        def respond(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, text=FIXTURE.read_text())

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            return collect_google_ai_blog(
                SQLiteNewsRepository(database), GoogleAiBlogFetcher(client), requested_at=NOW
            ).status

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(collect) for _ in range(2)]
        statuses = [future.result(timeout=10) for future in futures]
    assert sorted(statuses) == [CollectionStatus.COMPLETED, CollectionStatus.LIMIT_REACHED]
    assert len(calls) == 1
