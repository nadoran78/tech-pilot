"""Sequential collection with source-level failure isolation."""

import sqlite3
from collections.abc import Sequence
from dataclasses import replace

import httpx

from tech_pilot.collection.models import CollectionStatus, CollectionSummary
from tech_pilot.collection.registry import APPROVED_SOURCES, SourceRegistry
from tech_pilot.storage import SQLiteNewsRepository
from tech_pilot.storage.history import SQLiteRunHistory


def collect_sources(
    repository: SQLiteNewsRepository,
    client: httpx.Client,
    *,
    source_ids: Sequence[str] | None = None,
    history: SQLiteRunHistory,
    registry: SourceRegistry = APPROVED_SOURCES,
) -> tuple[CollectionSummary, ...]:
    """Complete all selected sources, preserving each source's request policy."""
    selected = tuple(dict.fromkeys(registry.source_ids if source_ids is None else source_ids))
    # Resolve the entire selection before any history or HTTP side effect.
    collectors = tuple((source, registry.collector(source)) for source in selected)
    results: list[CollectionSummary] = []
    for source, collect in collectors:
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
            result = collect(repository, client)
            if result.source_id != source:
                raise ValueError("collector source_id mismatch")
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
