"""Manual collection flow for the approved Hugging Face Blog RSS source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

import httpx

from tech_pilot.sources import SOURCE_ENDPOINT, SOURCE_ID, normalize_hugging_face_blog_feed
from tech_pilot.storage import HttpValidators, SQLiteNewsRepository, StoreStatus

DEFAULT_TIMEOUT_SECONDS = 10.0
USER_AGENT = "tech-pilot/0.1 (personal news collector)"


class FetchStatus(StrEnum):
    SUCCESS = "success"
    NOT_MODIFIED = "not_modified"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FetchResult:
    status: FetchStatus
    http_status: int | None
    body: str | None
    validators: HttpValidators
    error: str | None = None


class CollectionStatus(StrEnum):
    COMPLETED = "completed"
    UNCHANGED = "unchanged"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    source_id: str
    status: CollectionStatus
    http_status: int | None
    inserted: int = 0
    duplicates: int = 0
    review_required: int = 0
    skipped: int = 0
    error: str | None = None


class HuggingFaceBlogFetcher:
    """Fetch the approved RSS endpoint with optional conditional headers."""

    def __init__(
        self, client: httpx.Client, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ) -> None:
        self._client = client
        self._timeout_seconds = timeout_seconds

    def fetch(self, validators: HttpValidators | None) -> FetchResult:
        headers = {"User-Agent": USER_AGENT}
        if validators is not None and validators.etag is not None:
            headers["If-None-Match"] = validators.etag
        if validators is not None and validators.last_modified is not None:
            headers["If-Modified-Since"] = validators.last_modified

        try:
            response = self._client.get(
                SOURCE_ENDPOINT,
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except httpx.HTTPError:
            return FetchResult(
                status=FetchStatus.FAILED,
                http_status=None,
                body=None,
                validators=HttpValidators(),
                error="HTTP request failed",
            )

        response_validators = HttpValidators(
            etag=response.headers.get("ETag"),
            last_modified=response.headers.get("Last-Modified"),
        )
        if response.status_code == httpx.codes.NOT_MODIFIED:
            return FetchResult(
                status=FetchStatus.NOT_MODIFIED,
                http_status=response.status_code,
                body=None,
                validators=response_validators,
            )
        if not response.is_success:
            return FetchResult(
                status=FetchStatus.FAILED,
                http_status=response.status_code,
                body=None,
                validators=response_validators,
                error=f"HTTP {response.status_code}",
            )
        return FetchResult(
            status=FetchStatus.SUCCESS,
            http_status=response.status_code,
            body=response.text,
            validators=response_validators,
        )


def collect_hugging_face_blog(
    repository: SQLiteNewsRepository,
    fetcher: HuggingFaceBlogFetcher,
    *,
    collected_at: datetime | None = None,
) -> CollectionSummary:
    """Fetch, normalize, and store a single Hugging Face Blog RSS response."""

    previous_validators = repository.get_http_validators(SOURCE_ID)
    result = fetcher.fetch(previous_validators)
    if result.status is FetchStatus.FAILED:
        return CollectionSummary(
            source_id=SOURCE_ID,
            status=CollectionStatus.FAILED,
            http_status=result.http_status,
            error=result.error,
        )
    if result.status is FetchStatus.NOT_MODIFIED:
        if result.validators.has_values():
            repository.save_http_validators(SOURCE_ID, result.validators)
        return CollectionSummary(
            source_id=SOURCE_ID,
            status=CollectionStatus.UNCHANGED,
            http_status=result.http_status,
        )

    normalized = normalize_hugging_face_blog_feed(
        result.body or "",
        collected_at=collected_at or datetime.now(UTC),
    )
    if normalized.error is not None:
        return CollectionSummary(
            source_id=SOURCE_ID,
            status=CollectionStatus.FAILED,
            http_status=result.http_status,
            error=normalized.error,
        )
    inserted = 0
    duplicates = 0
    review_required = 0
    for item in normalized.items:
        store_result = repository.store(item)
        if store_result.status is StoreStatus.INSERTED:
            inserted += 1
        elif store_result.status is StoreStatus.DUPLICATE:
            duplicates += 1
        else:
            review_required += 1

    repository.save_http_validators(SOURCE_ID, result.validators)
    return CollectionSummary(
        source_id=SOURCE_ID,
        status=CollectionStatus.COMPLETED,
        http_status=result.http_status,
        inserted=inserted,
        duplicates=duplicates,
        review_required=review_required,
        skipped=len(normalized.skipped_entries),
    )
