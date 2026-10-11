"""Source-independent manual collection results."""

from dataclasses import dataclass
from enum import StrEnum


class CollectionStatus(StrEnum):
    COMPLETED = "completed"
    UNCHANGED = "unchanged"
    FAILED = "failed"
    LIMIT_REACHED = "limit_reached"


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
    history_error: str | None = None
