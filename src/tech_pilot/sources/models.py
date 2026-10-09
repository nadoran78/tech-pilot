"""Shared normalization results for RSS source adapters."""

from dataclasses import dataclass

from tech_pilot.storage import NewsItem


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
    error: str | None = None
