from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from tech_pilot.sources import SOURCE_ENDPOINT, SOURCE_ID, normalize_hugging_face_blog_feed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "hugging_face_blog_feed.xml"
COLLECTED_AT = datetime(2026, 9, 7, 1, 0, tzinfo=UTC)


def normalize_fixture():
    return normalize_hugging_face_blog_feed(
        FIXTURE_PATH.read_text(encoding="utf-8"), collected_at=COLLECTED_AT
    )


def test_normalizes_documented_rss_fields() -> None:
    result = normalize_fixture()
    first = result.items[0]

    assert first.source_id == SOURCE_ID
    assert first.external_id == "release-1"
    assert first.canonical_url == "https://huggingface.co/blog/valid-release"
    assert first.evidence_url == "https://huggingface.co/blog/valid-release#summary"
    assert first.title == "Valid release"
    assert first.published_at == datetime(2026, 9, 7, 9, 0, tzinfo=timezone(timedelta(hours=9)))
    assert first.published_at_raw == "Sun, 07 Sep 2026 09:00:00 +0900"
    assert first.collected_at == COLLECTED_AT
    assert first.source_endpoint == SOURCE_ENDPOINT


def test_uses_url_identity_when_guid_is_missing() -> None:
    result = normalize_fixture()
    item = result.items[1]

    assert item.external_id is None
    assert item.canonical_url == "https://huggingface.co/blog/url-identified"


def test_keeps_unparseable_date_as_raw_value_without_guessing() -> None:
    result = normalize_fixture()
    item = result.items[2]

    assert item.title == "Unparseable publication date"
    assert item.published_at is None
    assert item.published_at_raw == "not-a-date"


def test_skips_invalid_entries_without_stopping_other_normalization() -> None:
    result = normalize_fixture()

    assert [item.title for item in result.items] == [
        "Valid release",
        "URL identified entry",
        "Unparseable publication date",
    ]
    assert [(entry.index, entry.reason) for entry in result.skipped_entries] == [
        (2, "missing title"),
        (3, "canonical_url must be an absolute HTTP(S) URL"),
    ]
