"""Model-free orchestration with explicit processor injection and no retries."""

import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime

from tech_pilot.storage.understanding import SQLiteUnderstandingRepository
from tech_pilot.understanding.models import (
    ErrorCode,
    InputRejected,
    InputSnapshot,
    ProcessingOutcome,
    ProcessingRequest,
    UnderstandingResult,
    UnderstandingStorageError,
)

Processor = Callable[[InputSnapshot, ProcessingRequest], UnderstandingResult]


def process_news(
    repository: SQLiteUnderstandingRepository,
    news_id: int,
    request: ProcessingRequest,
    processor: Processor,
) -> ProcessingOutcome:
    """Persist one terminal attempt or reuse a completed result for the exact input."""
    if not isinstance(request, ProcessingRequest) or type(news_id) is not int or news_id < 1:
        raise InputRejected("invalid request or original reference")
    try:
        original = repository.get(news_id)
        if original is None:
            raise InputRejected("original reference is missing")
        snapshot = InputSnapshot.from_news(original)
        cached = repository.completed(request.reuse_key(snapshot))
        if cached is not None:
            return ProcessingOutcome(cached, reused=True)
        started_at = datetime.now(UTC)
        result = None
        error_code = None
        try:
            candidate = processor(snapshot, request)
        except Exception:  # Processor errors are untrusted; never persist exception text.
            error_code = ErrorCode.PROCESSING
        else:
            try:
                if not isinstance(candidate, UnderstandingResult):
                    raise ValueError("invalid processor result")
                candidate.validate(snapshot, request)
                result = candidate
            except (ValueError, TypeError, AttributeError):
                error_code = ErrorCode.VALIDATION
        attempt = repository.save_attempt(
            snapshot,
            request,
            started_at=started_at,
            result=result,
            error_code=error_code,
        )
        return ProcessingOutcome(attempt, reused=False)
    except InputRejected:
        raise
    except (sqlite3.Error, OSError, ValueError, TypeError):
        raise UnderstandingStorageError("understanding_storage_failed") from None
