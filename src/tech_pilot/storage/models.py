"""Data types shared by the local news-item repository."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit


def normalize_canonical_url(value: str) -> str:
    """Return a minimally normalized absolute HTTP(S) URL.

    Removing a fragment is safe across sources. Source-specific tracking
    parameter rules deliberately belong to source adapters and are not applied
    here.
    """

    url = value.strip()
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        msg = "canonical_url must be an absolute HTTP(S) URL"
        raise ValueError(msg)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def _require_text(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        msg = f"{name} must not be blank"
        raise ValueError(msg)
    return normalized


def _require_absolute_url(name: str, value: str) -> str:
    url = value.strip()
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        msg = f"{name} must be an absolute HTTP(S) URL"
        raise ValueError(msg)
    return url


@dataclass(frozen=True, slots=True)
class NewsItem:
    """A normalized news item ready for local persistence."""

    source_id: str
    canonical_url: str
    title: str
    collected_at: datetime
    evidence_url: str
    source_endpoint: str
    external_id: str | None = None
    published_at: datetime | None = None
    published_at_raw: str | None = None
    excerpt: str | None = None
    raw_metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _require_text("source_id", self.source_id))
        object.__setattr__(self, "canonical_url", normalize_canonical_url(self.canonical_url))
        object.__setattr__(self, "title", _require_text("title", self.title))
        object.__setattr__(
            self, "evidence_url", _require_absolute_url("evidence_url", self.evidence_url)
        )
        object.__setattr__(
            self, "source_endpoint", _require_absolute_url("source_endpoint", self.source_endpoint)
        )

        if self.collected_at.tzinfo is None:
            msg = "collected_at must include a timezone"
            raise ValueError(msg)
        if self.published_at is not None and self.published_at.tzinfo is None:
            msg = "published_at must include a timezone when present"
            raise ValueError(msg)

        if self.external_id is not None:
            external_id = self.external_id.strip()
            object.__setattr__(self, "external_id", external_id or None)


@dataclass(frozen=True, slots=True)
class StoredNewsItem:
    """A persisted news item with its repository identifier."""

    id: int
    item: NewsItem


class StoreStatus(StrEnum):
    INSERTED = "inserted"
    DUPLICATE = "duplicate"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True, slots=True)
class HttpValidators:
    """HTTP cache validators stored for one approved source."""

    etag: str | None = None
    last_modified: str | None = None

    def has_values(self) -> bool:
        return self.etag is not None or self.last_modified is not None


@dataclass(frozen=True, slots=True)
class StoreResult:
    """The result of attempting to persist a news item."""

    status: StoreStatus
    item_id: int | None
    reason: str
