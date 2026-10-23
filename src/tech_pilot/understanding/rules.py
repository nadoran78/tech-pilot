"""Deterministic title-only baseline; no fetching, translation or execution."""

import re
import unicodedata

from tech_pilot.understanding.models import (
    Category,
    ContentStatus,
    InputSnapshot,
    ProcessingRequest,
    RequestKind,
    UnderstandingResult,
)

METHOD = "title-rules"
PROCESSING_VERSION = "2"
RULESET_VERSION = "rules-v4"


def _terms(*terms: str) -> re.Pattern[str]:
    # Unicode boundaries intentionally do not implement Korean morphology.
    return re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, terms)) + r")(?!\w)", re.I)


_TECHNOLOGY = _terms(
    "model",
    "tool",
    "library",
    "framework",
    "sdk",
    "research",
    "모델",
    "도구",
    "라이브러리",
    "프레임워크",
    "연구",
)
_DEVELOPMENT = _terms(
    "introducing",
    "announcing",
    "release",
    "releases",
    "released",
    "launch",
    "launches",
    "launched",
    "공개",
    "출시",
    "발표",
    "cancel",
    "canceled",
    "cancelled",
    "cancellation",
    "delay",
    "delayed",
    "postpone",
    "postponed",
    "postponement",
    "withdrawal",
    "withdrawn",
    "update",
    "updates",
    "취소",
    "연기",
    "철회",
    "예정",
    "계획",
    "업데이트",
    "후속",
)
_USAGE = _terms("how to", "tutorial", "guide", "사용법", "튜토리얼", "활용 사례")
_NONTECHNICAL = _terms(
    "문화 행사",
    "채용 소식",
    "인사 소식",
    "cultural event",
    "hiring update",
    "leadership appointment",
)
# Mask URL spans rather than joining the surrounding words or changing source offsets.
_URL = re.compile(r"""(?:[a-z][a-z0-9+.-]*://|www\.)[^\s<>"'“”‘’「」『』`]+""", re.I)
_LABELS = {
    Category.TECHNOLOGY: "기술·제품 동향",
    Category.USAGE: "활용·해설",
    Category.NONTECHNICAL: "비기술 소식",
}


def rule_request(kind: RequestKind = RequestKind.DESCRIBE) -> ProcessingRequest:
    """Bind this implementation to its supported processing/rule identity."""
    return ProcessingRequest(kind, METHOD, PROCESSING_VERSION, RULESET_VERSION)


def _evidence(
    title: str, classification_text: str, patterns: tuple[re.Pattern[str], ...]
) -> tuple[str, ...]:
    matches = sorted(
        (match for pattern in patterns for match in pattern.finditer(classification_text)),
        key=lambda match: (match.start(), match.end()),
    )
    return tuple(dict.fromkeys(title[match.start() : match.end()] for match in matches))


def apply_title_rules(snapshot: InputSnapshot, request: ProcessingRequest) -> UnderstandingResult:
    """Return a constrained description or abstention, never a content summary."""
    if request != rule_request(request.kind):
        raise ValueError("unsupported rule processing identity")
    title = snapshot.title
    if (
        not title.strip()
        or len(title) > 2000
        or any(
            unicodedata.category(char).startswith("C") or char in "\u2028\u2029" for char in title
        )
    ):
        return UnderstandingResult(ContentStatus.DEFERRED, reason="처리할 수 없는 제목 형식")
    classification_text = _URL.sub(lambda match: " " * len(match.group()), title)

    candidates: dict[Category, tuple[str, ...]] = {}
    if _TECHNOLOGY.search(classification_text):
        if _DEVELOPMENT.search(classification_text):
            candidates[Category.TECHNOLOGY] = _evidence(
                title, classification_text, (_TECHNOLOGY, _DEVELOPMENT)
            )
        if _USAGE.search(classification_text):
            candidates[Category.USAGE] = _evidence(
                title, classification_text, (_TECHNOLOGY, _USAGE)
            )
    if _NONTECHNICAL.search(classification_text):
        candidates[Category.NONTECHNICAL] = _evidence(title, classification_text, (_NONTECHNICAL,))

    category = Category.UNKNOWN
    evidence: tuple[str, ...] = ()
    if len(candidates) == 1:
        category, evidence = next(iter(candidates.items()))
    if request.kind is RequestKind.SUMMARIZE:
        return UnderstandingResult(
            ContentStatus.INSUFFICIENT,
            category,
            evidence=evidence,
            reason="제목만으로 원문 내용 요약 불가",
        )
    if len(candidates) != 1:
        reason = "범주 충돌로 판단 불가" if candidates else "지원 규칙의 명확한 제목 근거 부족"
        return UnderstandingResult(ContentStatus.INSUFFICIENT, reason=reason)
    return UnderstandingResult(
        ContentStatus.DESCRIBED,
        category,
        text=f"제목 기반 설명(잠정 분류: {_LABELS[category]}): 「{title}」",
        evidence=evidence,
    )
