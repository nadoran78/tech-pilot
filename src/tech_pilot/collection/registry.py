"""Explicit source registration; registering code is not operational approval."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import httpx

from tech_pilot.collection.google_ai_blog import GoogleAiBlogFetcher, collect_google_ai_blog
from tech_pilot.collection.hugging_face_blog import (
    HuggingFaceBlogFetcher,
    collect_hugging_face_blog,
)
from tech_pilot.collection.models import CollectionSummary
from tech_pilot.storage import SQLiteNewsRepository

Collector = Callable[[SQLiteNewsRepository, httpx.Client], CollectionSummary]


@dataclass(frozen=True, slots=True)
class SourceRegistration:
    source_id: str
    collect: Collector


class SourceRegistry:
    """An ordered snapshot, separate from test registries and runtime configuration."""

    def __init__(self, entries: Sequence[SourceRegistration]) -> None:
        collectors: dict[str, Collector] = {}
        for entry in entries:
            if not entry.source_id or entry.source_id != entry.source_id.strip():
                raise ValueError("source_id must be nonblank and trimmed")
            if entry.source_id in collectors:
                raise ValueError("duplicate source_id")
            if not callable(entry.collect):
                raise ValueError("collector must be callable")
            collectors[entry.source_id] = entry.collect
        self._collectors = MappingProxyType(collectors)

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(self._collectors)

    def collector(self, source_id: str) -> Collector:
        try:
            return self._collectors[source_id]
        except KeyError as error:
            raise ValueError("unknown source") from error


def _collect_hugging_face(
    repository: SQLiteNewsRepository, client: httpx.Client
) -> CollectionSummary:
    return collect_hugging_face_blog(repository, HuggingFaceBlogFetcher(client))


def _collect_google(repository: SQLiteNewsRepository, client: httpx.Client) -> CollectionSummary:
    return collect_google_ai_blog(repository, GoogleAiBlogFetcher(client))


# Only sources whose limited manual operation has been approved belong here.
APPROVED_SOURCES = SourceRegistry(
    (
        SourceRegistration("hugging-face-blog", _collect_hugging_face),
        SourceRegistration("google-ai-blog", _collect_google),
    )
)
