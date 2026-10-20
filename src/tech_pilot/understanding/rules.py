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
PROCESSING_VERSION = "1"
RULESET_VERSION = "rules-v1"


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
_RELEASE = _terms(
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
_CAUTION_EN = _terms(
    "no",
    "not",
    "never",
    "without",
    "isn't",
    "doesn't",
    "won't",
    "cannot",
    "can't",
    "may",
    "might",
    "rumor",
    "rumors",
    "expected",
    "planned",
    "will",
    "ignore",
    "instruction",
    "instructions",
    "execute",
    "run",
)
_CAUTION_KO = re.compile(
    "아님|아니다|아닌|않|안|못|없|예정|계획|루머|추측|검토|불가|취소|무시|명령|실행"
)
_QUOTES_URL_QUESTION = re.compile(r"""[?？"'`“”‘’「」『』]|https?://|www\.""", re.I)
_LABELS = {
    Category.TECHNOLOGY: "기술 발표",
    Category.USAGE: "활용·해설",
    Category.NONTECHNICAL: "비기술 소식",
}


def rule_request(kind: RequestKind = RequestKind.DESCRIBE) -> ProcessingRequest:
    """Bind this implementation to its supported processing/rule identity."""
    return ProcessingRequest(kind, METHOD, PROCESSING_VERSION, RULESET_VERSION)


def _evidence(title: str, patterns: tuple[re.Pattern[str], ...]) -> tuple[str, ...]:
    matches = sorted(
        (match for pattern in patterns for match in pattern.finditer(title)),
        key=lambda match: (match.start(), match.end()),
    )
    return tuple(dict.fromkeys(match.group() for match in matches))


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
    if _CAUTION_EN.search(title) or _CAUTION_KO.search(title) or _QUOTES_URL_QUESTION.search(title):
        return UnderstandingResult(
            ContentStatus.INSUFFICIENT, reason="부정·불확실성·인용·지시문 등으로 제목 판단 보류"
        )

    candidates: dict[Category, tuple[str, ...]] = {}
    if _TECHNOLOGY.search(title):
        if _RELEASE.search(title):
            candidates[Category.TECHNOLOGY] = _evidence(title, (_TECHNOLOGY, _RELEASE))
        if _USAGE.search(title):
            candidates[Category.USAGE] = _evidence(title, (_TECHNOLOGY, _USAGE))
    if _NONTECHNICAL.search(title):
        candidates[Category.NONTECHNICAL] = _evidence(title, (_NONTECHNICAL,))

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
