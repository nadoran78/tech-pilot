from datetime import UTC, datetime
from pathlib import Path

from tech_pilot.sources.google_ai_blog import SOURCE_ID, normalize_google_ai_blog_feed

FIXTURE = Path(__file__).parent / "fixtures" / "google_ai_blog_feed.xml"
NOW = datetime(2026, 10, 9, 1, tzinfo=UTC)


def test_normalizes_only_approved_metadata_and_excludes_invalid_entries() -> None:
    result = normalize_google_ai_blog_feed(FIXTURE.read_text(), collected_at=NOW)
    assert result.error is None
    assert len(result.items) == 2
    assert len(result.skipped_entries) == 3
    first, no_date = result.items
    assert first.source_id == SOURCE_ID
    assert first.external_id == "test-1"
    assert first.canonical_url == "https://example.com/release"
    assert first.published_at == datetime(2026, 10, 9, tzinfo=UTC)
    assert first.published_at_raw == "Fri, 09 Oct 2026 00:00:00 +0000"
    assert first.collected_at == NOW
    assert first.excerpt is None
    assert first.raw_metadata is None
    assert no_date.published_at is None


def test_rejects_malformed_feed() -> None:
    result = normalize_google_ai_blog_feed("<rss><channel>", collected_at=NOW)
    assert result.error == "RSS parsing failed"
    assert result.items == ()
