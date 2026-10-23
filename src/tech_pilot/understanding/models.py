"""Immutable input, request and structurally validated title-level results."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum

from tech_pilot.storage.models import StoredNewsItem


class RequestKind(StrEnum):
    DESCRIBE = "describe_title"
    SUMMARIZE = "summarize_content"


class ContentStatus(StrEnum):
    DESCRIBED = "described"
    INSUFFICIENT = "insufficient_information"
    DEFERRED = "deferred"
    SUMMARIZED = "summarized"  # Representable for validation, never valid for title input.


class Category(StrEnum):
    # Legacy wire value retained for technology/product developments, not launch verification.
    TECHNOLOGY = "technology_release"
    USAGE = "usage_explanation"
    NONTECHNICAL = "nontechnical"
    UNKNOWN = "unknown"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class InputSnapshot:
    news_id: int
    source_id: str
    evidence_url: str
    title: str
    published_at: str | None

    @classmethod
    def from_news(cls, stored: StoredNewsItem) -> "InputSnapshot":
        item = stored.item
        return cls(
            stored.id,
            item.source_id,
            item.evidence_url,
            item.title,
            item.published_at.isoformat() if item.published_at else None,
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(canonical_json(asdict(self)).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ProcessingRequest:
    kind: RequestKind
    method: str
    processing_version: str
    configuration_version: str
    input_version: str = "title-v1"
    output_version: str = "title-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.kind, RequestKind):
            raise ValueError("invalid request kind")
        if self.input_version != "title-v1" or self.output_version != "title-v1":
            raise ValueError("unsupported contract version")
        for value in (self.method, self.processing_version, self.configuration_version):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise ValueError("invalid processing identity")

    def reuse_key(self, snapshot: InputSnapshot) -> str:
        payload = {
            "news_id": snapshot.news_id,
            "fingerprint": snapshot.fingerprint,
            "request": asdict(self),
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class UnderstandingResult:
    status: ContentStatus
    category: Category = Category.UNKNOWN
    text: str | None = None
    evidence: tuple[str, ...] = ()
    reason: str | None = None
    limitation: str = "원문 미열람"

    def validate(self, snapshot: InputSnapshot, request: ProcessingRequest) -> None:
        if not isinstance(self.status, ContentStatus) or not isinstance(self.category, Category):
            raise ValueError("invalid result state")
        if self.limitation != "원문 미열람":
            raise ValueError("title limitation is required")
        if self.reason is not None and (
            not isinstance(self.reason, str) or not self.reason.strip()
        ):
            raise ValueError("invalid reason")
        if self.status is ContentStatus.SUMMARIZED:
            raise ValueError("content summary forbidden for title input")
        if request.kind is RequestKind.SUMMARIZE and self.status not in {
            ContentStatus.INSUFFICIENT,
            ContentStatus.DEFERRED,
        }:
            raise ValueError("summary request requires abstention")
        if self.status is ContentStatus.DESCRIBED:
            if not isinstance(self.text, str) or not self.text.strip() or not self.evidence:
                raise ValueError("description requires text and evidence")
        elif self.text is not None or not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("abstention requires no text and a reason")
        if self.category is not Category.UNKNOWN and not self.evidence:
            raise ValueError("classification requires evidence")
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(part, str) or not part.strip() or part not in snapshot.title
            for part in self.evidence
        ):
            raise ValueError("evidence must be exact title spans")


class ExecutionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(StrEnum):
    PROCESSING = "processing_failed"
    VALIDATION = "validation_failed"


@dataclass(frozen=True, slots=True)
class StoredAttempt:
    id: int
    reuse_key: str
    snapshot: InputSnapshot
    request: ProcessingRequest
    started_at: datetime
    finished_at: datetime
    status: ExecutionStatus
    result: UnderstandingResult | None
    error_code: ErrorCode | None


@dataclass(frozen=True, slots=True)
class ProcessingOutcome:
    attempt: StoredAttempt
    reused: bool


class InputRejected(ValueError):
    """No processing/attempt is created for an invalid original reference."""


class UnderstandingStorageError(RuntimeError):
    """Safe failure: persistence is not reported as completed."""
