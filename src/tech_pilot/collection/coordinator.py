"""Sequential collection with source-level failure isolation."""

import sqlite3
from collections.abc import Sequence
from dataclasses import replace

import httpx

from tech_pilot.collection.google_ai_blog import GoogleAiBlogFetcher, collect_google_ai_blog
from tech_pilot.collection.hugging_face_blog import (
    HuggingFaceBlogFetcher,
    collect_hugging_face_blog,
)
from tech_pilot.collection.models import CollectionStatus, CollectionSummary
from tech_pilot.storage import SQLiteNewsRepository
from tech_pilot.storage.history import SQLiteRunHistory

SOURCE_IDS = ("hugging-face-blog", "google-ai-blog")


def collect_sources(
    repository: SQLiteNewsRepository,
    client: httpx.Client,
    *,
    source_ids: Sequence[str] = SOURCE_IDS,
    history: SQLiteRunHistory,
) -> tuple[CollectionSummary, ...]:
    """Complete all selected sources, preserving each source's request policy."""
    if any(source not in SOURCE_IDS for source in source_ids):
        raise ValueError("unknown source")
    results: list[CollectionSummary] = []
    for source in dict.fromkeys(source_ids):
        try:
            run_id = history.start(source)
        except (sqlite3.Error, OSError, ValueError):
            results.append(
                CollectionSummary(
                    source, CollectionStatus.FAILED, None, history_error="history_start_failed"
                )
            )
            continue
        try:
            if source == "hugging-face-blog":
                result = collect_hugging_face_blog(repository, HuggingFaceBlogFetcher(client))
            else:
                result = collect_google_ai_blog(repository, GoogleAiBlogFetcher(client))
        except (sqlite3.Error, OSError, ValueError):
            result = CollectionSummary(
                source, CollectionStatus.FAILED, None, error="Source collection failed"
            )
        code = None
        if result.status is CollectionStatus.FAILED:
            code = {
                "HTTP request failed": "request_failed",
                "RSS parsing failed": "parse_failed",
            }.get(
                result.error or "",
                "http_failed" if (result.error or "").startswith("HTTP ") else "local_failed",
            )
        try:
            history.finish(
                run_id,
                status=result.status.value,
                http_status=result.http_status,
                counts=(result.inserted, result.duplicates, result.review_required, result.skipped),
                error_code=code,
            )
        except (sqlite3.Error, OSError, ValueError):
            result = replace(result, history_error="history_finish_failed")
        results.append(result)
    return tuple(results)
