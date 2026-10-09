"""Minimal metadata normalization for Google AI Blog RSS."""

from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import feedparser  # type: ignore[import-untyped]

from tech_pilot.sources.hugging_face_blog import RssNormalizationResult, SkippedRssEntry
from tech_pilot.storage import NewsItem

SOURCE_ID = "google-ai-blog"
SOURCE_ENDPOINT = "https://blog.google/innovation-and-ai/technology/ai/rss/"


def normalize_google_ai_blog_feed(
    feed_xml: str, *, collected_at: datetime
) -> RssNormalizationResult:
    """Exclude invalid entries while preserving only approved metadata."""
    parsed = feedparser.parse(feed_xml)
    if parsed.bozo or not parsed.version:
        return RssNormalizationResult((), (), "RSS parsing failed")
    items: list[NewsItem] = []
    skipped: list[SkippedRssEntry] = []
    for index, entry in enumerate(parsed.entries):
        title = str(entry.get("title", "")).strip()
        link = str(entry.get("link", "")).strip()
        try:
            parts = urlsplit(link)
        except ValueError:
            skipped.append(SkippedRssEntry(index, "invalid HTTPS link"))
            continue
        if not title or parts.scheme != "https" or not parts.netloc:
            skipped.append(SkippedRssEntry(index, "missing title or invalid HTTPS link"))
            continue
        raw = entry.get("published")
        raw = raw.strip() if isinstance(raw, str) else None
        published = None
        if raw:
            try:
                published = parsedate_to_datetime(raw)
                if published.utcoffset() is None:
                    raise ValueError("missing timezone")
            except (IndexError, TypeError, ValueError):
                skipped.append(SkippedRssEntry(index, "invalid published time"))
                continue
        external_id = entry.get("id")
        items.append(
            NewsItem(
                source_id=SOURCE_ID,
                external_id=external_id if isinstance(external_id, str) else None,
                canonical_url=link,
                evidence_url=link,
                title=title,
                published_at=published,
                published_at_raw=raw,
                collected_at=collected_at,
                source_endpoint=SOURCE_ENDPOINT,
            )
        )
    return RssNormalizationResult(tuple(items), tuple(skipped))
