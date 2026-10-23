"""Manual command handlers, safe rendering and no network dependency."""

import sqlite3
import unicodedata
from pathlib import Path
from typing import TextIO

from tech_pilot.storage.understanding import SQLiteUnderstandingRepository
from tech_pilot.understanding.models import (
    Category,
    ContentStatus,
    ExecutionStatus,
    InputRejected,
    InputSnapshot,
    StoredAttempt,
    UnderstandingStorageError,
)
from tech_pilot.understanding.rules import rule_request
from tech_pilot.understanding.service import process_title_with_rules

_CATEGORIES = {
    Category.TECHNOLOGY: "기술·제품 동향",
    Category.USAGE: "활용·해설",
    Category.NONTECHNICAL: "비기술 소식",
    Category.UNKNOWN: "판단 불가",
}
_CONTENT = {
    ContentStatus.DESCRIBED: "제목 기반 설명",
    ContentStatus.INSUFFICIENT: "정보 부족",
    ContentStatus.DEFERRED: "보류",
    ContentStatus.SUMMARIZED: "내용 요약(과거 기록)",
}


def safe_text(value: object) -> str:
    """Keep terminal controls, bidi overrides and line separators inert."""
    return "".join(
        f"\\u{ord(char):04x}"
        if unicodedata.category(char).startswith("C") or char in "\u2028\u2029"
        else char
        for char in str(value)
    )


def _write_attempt(output: TextIO, attempt: StoredAttempt, relevance: str) -> None:
    request = attempt.request
    execution = "완료" if attempt.status is ExecutionStatus.COMPLETED else "실패"
    print(
        f"시도 #{attempt.id}: 뉴스 #{safe_text(attempt.snapshot.news_id)}, 구분={relevance}, "
        f"실행={execution}({attempt.status}), 요청={safe_text(request.kind)}",
        file=output,
    )
    print(
        f"  당시 제목={safe_text(attempt.snapshot.title)}, "
        f"출처={safe_text(attempt.snapshot.source_id)}, "
        f"원문={safe_text(attempt.snapshot.evidence_url)}",
        file=output,
    )
    print(
        f"  방법={safe_text(request.method)}, 처리 버전={safe_text(request.processing_version)}, "
        f"규칙 버전={safe_text(request.configuration_version)}, "
        f"입출력={safe_text(request.input_version)}/{safe_text(request.output_version)}",
        file=output,
    )
    print(
        f"  시작={safe_text(attempt.started_at.isoformat())}, "
        f"종료={safe_text(attempt.finished_at.isoformat())}",
        file=output,
    )
    if attempt.result is None:
        print(f"  결과 없음, 오류 코드={safe_text(attempt.error_code)}", file=output)
        return
    result = attempt.result
    print(
        f"  내용={_CONTENT[result.status]}({result.status}), "
        f"잠정 분류={_CATEGORIES[result.category]}({result.category})",
        file=output,
    )
    print(
        f"  설명={safe_text(result.text) if result.text is not None else '-'}, "
        f"근거={safe_text(' / '.join(result.evidence)) or '-'}",
        file=output,
    )
    print(
        f"  한계={safe_text(result.limitation)}, "
        f"사유={safe_text(result.reason) if result.reason is not None else '-'}",
        file=output,
    )


def _relevance(attempt: StoredAttempt, snapshot: InputSnapshot | None) -> str:
    if snapshot is None:
        return "원본 없음(당시 입력)"
    current_key = rule_request(attempt.request.kind).reuse_key(snapshot)
    return "현재 입력·버전" if attempt.reuse_key == current_key else "과거 입력·버전"


def understand_one(database: Path, news_id: int, output: TextIO) -> int:
    repository = SQLiteUnderstandingRepository(database)
    try:
        # Validate the reference read-only before the write path can migrate an old DB.
        original, _ = repository.read_history(news_id, limit=1)
        if original is None:
            raise InputRejected("missing original")
        outcome = process_title_with_rules(repository, news_id)
        print("처리 결과: " + ("재사용" if outcome.reused else "새 처리"), file=output)
        _write_attempt(output, outcome.attempt, "현재 입력·버전")
        return int(outcome.attempt.status is ExecutionStatus.FAILED)
    except InputRejected:
        print("뉴스 원본이 없거나 변경되었습니다: understanding_input_rejected", file=output)
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, UnderstandingStorageError):
        print("뉴스 처리 실패: understanding_operation_failed", file=output)
    return 1


def show_understanding_history(database: Path, news_id: int, limit: int, output: TextIO) -> int:
    try:
        original, attempts = SQLiteUnderstandingRepository(database).read_history(
            news_id, limit=limit
        )
        if not attempts:
            print("설명·분류 처리 이력이 없습니다.", file=output)
            return 0
        for attempt in attempts:
            _write_attempt(output, attempt, _relevance(attempt, original))
        return 0
    except (sqlite3.Error, OSError, ValueError, TypeError, KeyError):
        print("설명·분류 이력 조회 실패: understanding_read_failed", file=output)
        return 1
