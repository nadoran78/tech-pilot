"""Sequential collection with source-level failure isolation."""

import sqlite3
from collections.abc import Sequence

import httpx

from tech_pilot.collection.google_ai_blog import GoogleAiBlogFetcher, collect_google_ai_blog
from tech_pilot.collection.hugging_face_blog import (
    HuggingFaceBlogFetcher,
    collect_hugging_face_blog,
)
from tech_pilot.collection.models import CollectionStatus, CollectionSummary
from tech_pilot.storage import SQLiteNewsRepository

SOURCE_IDS = ("hugging-face-blog", "google-ai-blog")


def collect_sources(
    repository: SQLiteNewsRepository,
    client: httpx.Client,
    *,
    source_ids: Sequence[str] = SOURCE_IDS,
) -> tuple[CollectionSummary, ...]:
    """Complete all selected sources, preserving each source's request policy."""
    if any(source not in SOURCE_IDS for source in source_ids):
        raise ValueError("unknown source")
    results: list[CollectionSummary] = []
    for source in dict.fromkeys(source_ids):
        try:
            if source == "hugging-face-blog":
                result = collect_hugging_face_blog(repository, HuggingFaceBlogFetcher(client))
            else:
                result = collect_google_ai_blog(repository, GoogleAiBlogFetcher(client))
        except (sqlite3.Error, OSError, ValueError):
            result = CollectionSummary(
                source, CollectionStatus.FAILED, None, error="Source collection failed"
            )
        results.append(result)
    return tuple(results)
