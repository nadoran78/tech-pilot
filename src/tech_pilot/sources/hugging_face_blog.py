"""Fixture-friendly normalization for the approved Hugging Face Blog RSS feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Mapping

import feedparser  # type: ignore[import-untyped]

from tech_pilot.storage import NewsItem

SOURCE_ID = "hugging-face-blog"
SOURCE_ENDPOINT = "https://huggingface.co/blog/feed.xml"


@dataclass(frozen=True, slots=True)
class SkippedRssEntry:
    """An RSS entry excluded from normalization without stopping its feed."""

    index: int
    reason: str


@dataclass(frozen=True, slots=True)
class RssNormalizationResult:
    """Normalized items and safe exclusions from one RSS document."""

    items: tuple[NewsItem, ...]
    skipped_entries: tuple[SkippedRssEntry, ...]


def normalize_hugging_face_blog_feed(
    feed_xml: str, *, collected_at: datetime
) -> RssNormalizationResult:
    """Normalize one Hugging Face Blog RSS document without making HTTP requests."""

    parsed_feed = feedparser.parse(feed_xml)
    items: list[NewsItem] = []
    skipped_entries: list[SkippedRssEntry] = []

    for index, entry in enumerate(parsed_feed.entries):
        normalized_item, reason = _normalize_entry(entry, collected_at=collected_at)
        if normalized_item is not None:
            items.append(normalized_item)
        else:
            skipped_entries.append(SkippedRssEntry(index=index, reason=reason))

    return RssNormalizationResult(
        items=tuple(items),
        skipped_entries=tuple(skipped_entries),
    )


def _normalize_entry(
    entry: Mapping[str, object], *, collected_at: datetime
) -> tuple[NewsItem | None, str]:
    title = _entry_text(entry, "title")
    if title is None:
        return None, "missing title"

    link = _entry_text(entry, "link")
    if link is None:
        return None, "missing link"

    published_at_raw = _entry_text(entry, "published")
    try:
        return (
            NewsItem(
                source_id=SOURCE_ID,
                external_id=_entry_text(entry, "id") or _entry_text(entry, "guid"),
                canonical_url=link,
                title=title,
                published_at=_parse_published_at(published_at_raw),
                published_at_raw=published_at_raw,
                collected_at=collected_at,
                evidence_url=link,
                source_endpoint=SOURCE_ENDPOINT,
            ),
            "",
        )
    except ValueError as error:
        return None, str(error)


def _entry_text(entry: Mapping[str, object], key: str) -> str | None:
    value = entry.get(key)
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _parse_published_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (IndexError, TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None
