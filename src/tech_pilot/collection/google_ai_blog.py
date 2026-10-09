"""Manual Google RSS collection with persistent daily request reservation."""

from datetime import UTC, datetime

import httpx

from tech_pilot.collection.models import CollectionStatus, CollectionSummary
from tech_pilot.sources.google_ai_blog import (
    SOURCE_ENDPOINT,
    SOURCE_ID,
    normalize_google_ai_blog_feed,
)
from tech_pilot.storage import DailyRequestReservationStatus, SQLiteNewsRepository, StoreStatus

USER_AGENT = "tech-pilot/0.1 (personal news collector)"


class GoogleAiBlogFetcher:
    """Send exactly one GET without redirects or conditional requests."""

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def fetch(self) -> httpx.Response:
        return self._client.get(
            SOURCE_ENDPOINT,
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
            follow_redirects=False,
        )


def collect_google_ai_blog(
    repository: SQLiteNewsRepository,
    fetcher: GoogleAiBlogFetcher,
    *,
    requested_at: datetime | None = None,
) -> CollectionSummary:
    """Reserve before HTTP; retain the reservation for every failure outcome."""
    now = requested_at or datetime.now(UTC)
    reservation = repository.reserve_daily_request(SOURCE_ID, requested_at=now)
    if reservation.status is DailyRequestReservationStatus.ALREADY_RESERVED:
        return CollectionSummary(SOURCE_ID, CollectionStatus.LIMIT_REACHED, None)
    try:
        response = fetcher.fetch()
    except httpx.HTTPError:
        return CollectionSummary(
            SOURCE_ID, CollectionStatus.FAILED, None, error="HTTP request failed"
        )
    if not response.is_success:
        return CollectionSummary(
            SOURCE_ID,
            CollectionStatus.FAILED,
            response.status_code,
            error=f"HTTP {response.status_code}",
        )
    normalized = normalize_google_ai_blog_feed(response.text, collected_at=now)
    if normalized.error:
        return CollectionSummary(
            SOURCE_ID, CollectionStatus.FAILED, response.status_code, error=normalized.error
        )
    counts = dict.fromkeys(StoreStatus, 0)
    for item in normalized.items:
        counts[repository.store(item).status] += 1
    return CollectionSummary(
        SOURCE_ID,
        CollectionStatus.COMPLETED,
        response.status_code,
        inserted=counts[StoreStatus.INSERTED],
        duplicates=counts[StoreStatus.DUPLICATE],
        review_required=counts[StoreStatus.REVIEW_REQUIRED],
        skipped=len(normalized.skipped_entries),
    )
