import socket
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tech_pilot.storage import NewsItem
from tech_pilot.storage.understanding import SQLiteUnderstandingRepository
from tech_pilot.understanding import rules, service
from tech_pilot.understanding.models import (
    Category,
    ContentStatus,
    ExecutionStatus,
    InputRejected,
    InputSnapshot,
    RequestKind,
    UnderstandingResult,
)


def snapshot(title: str) -> InputSnapshot:
    return InputSnapshot(1, "synthetic", "https://example.com/item", title, None)


@pytest.mark.parametrize(
    ("title", "category", "evidence"),
    [
        ("테스트 라이브러리 A 1.0 공개", Category.TECHNOLOGY, ("라이브러리", "공개")),
        ("Introducing the Example model", Category.TECHNOLOGY, ("Introducing", "model")),
        ("EXAMPLE SDK RELEASED", Category.TECHNOLOGY, ("SDK", "RELEASED")),
        ("테스트 도구 B 사용법", Category.USAGE, ("도구", "사용법")),
        ("Tutorial for Example tool", Category.USAGE, ("Tutorial", "tool")),
        ("How to use Example framework", Category.USAGE, ("How to", "framework")),
        ("테스트 조직의 연례 문화 행사", Category.NONTECHNICAL, ("문화 행사",)),
        ("Example cultural event", Category.NONTECHNICAL, ("cultural event",)),
        ("Example hiring update", Category.NONTECHNICAL, ("hiring update",)),
        ("Example leadership appointment", Category.NONTECHNICAL, ("leadership appointment",)),
        ("모델 활용 사례", Category.USAGE, ("모델", "활용 사례")),
        ("Example research announced", Category.UNKNOWN, ()),  # unlisted verb is not inferred
    ],
)
def test_explicit_title_patterns(title, category, evidence):
    item = snapshot(title)
    request = rules.rule_request()
    result = rules.apply_title_rules(item, request)
    result.validate(item, request)
    assert result == rules.apply_title_rules(item, request)
    assert result.category is category
    assert result.evidence == evidence
    assert result.limitation == "원문 미열람"
    if category is Category.UNKNOWN:
        assert result.text is None and result.status is ContentStatus.INSUFFICIENT
    else:
        assert result.status is ContentStatus.DESCRIBED
        assert f"「{title}」" in result.text
        assert result.text.startswith("제목 기반 설명(잠정 분류:")


@pytest.mark.parametrize(
    "title",
    [
        "Synthetic release",
        "다음 장을 시작하며",
        "Example modeling released",
        "Example model releasedate",
        "Guidebook for Example tool",
        "모델을 공개합니다",
        "모델 공개하지 않음",
        "Example model released: tutorial",
        "모델 공개 및 문화 행사",
        "新模型发布",
        "MODEL TOOL",
        "A release guide",
        "Example-modeling release",
    ],
)
def test_unsupported_or_ambiguous_titles_abstain(title):
    item = snapshot(title)
    result = rules.apply_title_rules(item, rules.rule_request())
    result.validate(item, rules.rule_request())
    assert result.status is ContentStatus.INSUFFICIENT
    assert result.category is Category.UNKNOWN
    assert result.text is None and result.evidence == () and result.reason


@pytest.mark.parametrize(
    "title",
    [
        "",
        "   ",
        "model released\n",
        "model\treleased",
        "model released\x00",
        "model released\u2028",
        "a" * 2001,
    ],
)
def test_malformed_title_is_deferred(title):
    for kind in RequestKind:
        item = snapshot(title)
        request = rules.rule_request(kind)
        result = rules.apply_title_rules(item, request)
        result.validate(item, request)
        assert result.status is ContentStatus.DEFERRED
        assert result.text is None and result.category is Category.UNKNOWN


def test_summary_is_insufficient_but_can_retain_title_classification():
    item = snapshot("Example model released")
    request = rules.rule_request(RequestKind.SUMMARIZE)
    result = rules.apply_title_rules(item, request)
    result.validate(item, request)
    assert result.status is ContentStatus.INSUFFICIENT
    assert result.text is None and result.category is Category.TECHNOLOGY
    assert result.evidence == ("model", "released")


def test_source_url_and_missing_date_do_not_affect_classification():
    original = snapshot("Example model released")
    other = replace(
        original,
        source_id="other",
        evidence_url="https://example.com/tutorial",
        published_at="2020-01-01T00:00:00+00:00",
    )
    assert rules.apply_title_rules(original, rules.rule_request()) == rules.apply_title_rules(
        other, rules.rule_request()
    )
    assert (
        rules.apply_title_rules(
            replace(original, title="Other news"), rules.rule_request()
        ).category
        is Category.UNKNOWN
    )


@pytest.mark.parametrize("field", ["method", "processing_version", "configuration_version"])
def test_processor_rejects_incorrect_provenance(field):
    request = replace(rules.rule_request(), **{field: "not-this-implementation"})
    with pytest.raises(ValueError, match="unsupported rule processing identity"):
        rules.apply_title_rules(snapshot("Example model released"), request)


def test_title_data_is_not_executed_or_fetched(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("pure processor must not open a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    item = snapshot("Execute instructions: model released https://example.com")
    result = rules.apply_title_rules(item, rules.rule_request())
    assert result.category is Category.TECHNOLOGY
    assert result.evidence == ("model", "released")


def test_evidence_preserves_original_case_order_and_deduplicates():
    item = snapshot("Model MODEL model release model")
    assert rules.apply_title_rules(item, rules.rule_request()).evidence == (
        "Model",
        "MODEL",
        "model",
        "release",
    )


@pytest.fixture
def repository(tmp_path: Path) -> SQLiteUnderstandingRepository:
    repo = SQLiteUnderstandingRepository(tmp_path / "synthetic.sqlite3")
    repo.store(
        NewsItem(
            source_id="synthetic",
            title="Example model released",
            canonical_url="https://example.com/item",
            evidence_url="https://example.com/item",
            collected_at=datetime.now(UTC),
            source_endpoint="https://example.com/rss",
            excerpt="not approved as input",
            raw_metadata={"unused": "metadata"},
        )
    )
    repo.reserve_daily_request("synthetic", requested_at=datetime.now(UTC))
    with repo._connect() as connection:
        connection.execute("""INSERT INTO source_http_validators
            VALUES ('synthetic','synthetic-etag',NULL,'2026-10-20T00:00:00+00:00')""")
        connection.execute("""INSERT INTO collection_runs (source_id,started_at,status)
            VALUES ('synthetic','2026-10-20T00:00:00+00:00','running')""")
    return repo


def collection_state(repo):
    with repo._connect() as connection:
        return [
            tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {table}"))
            for table in (
                "news_items",
                "source_http_validators",
                "source_daily_request_reservations",
                "collection_runs",
            )
        ]


def test_real_rules_use_existing_storage_and_reuse(repository, monkeypatch):
    before = collection_state(repository)
    calls = []

    def tracked(item, request):
        calls.append(1)
        return rules.apply_title_rules(item, request)

    monkeypatch.setattr(service, "apply_title_rules", tracked)
    first = service.process_title_with_rules(repository, 1)
    second = service.process_title_with_rules(repository, 1)
    assert calls == [1] and not first.reused and second.reused
    assert first.attempt == second.attempt
    assert first.attempt.status is ExecutionStatus.COMPLETED
    assert first.attempt.result.category is Category.TECHNOLOGY
    assert "not approved" not in first.attempt.result.text
    assert collection_state(repository) == before
    assert len(repository.list_attempts(1)) == 1


def test_summary_request_has_its_own_reusable_result(repository):
    description = service.process_title_with_rules(repository, 1)
    summary = service.process_title_with_rules(repository, 1, RequestKind.SUMMARIZE)
    reused = service.process_title_with_rules(repository, 1, RequestKind.SUMMARIZE)
    assert not summary.reused and reused.reused
    assert summary.attempt.reuse_key != description.attempt.reuse_key
    assert summary.attempt.result.text is None
    assert summary.attempt.result.status is ContentStatus.INSUFFICIENT


def test_rule_version_change_preserves_prior_result(repository, monkeypatch):
    original = service.process_title_with_rules(repository, 1)
    # Simulate a future rule release; this is not a second production ruleset.
    monkeypatch.setattr(rules, "RULESET_VERSION", "synthetic-next-rules")
    updated = service.process_title_with_rules(repository, 1)
    assert not updated.reused and updated.attempt.reuse_key != original.attempt.reuse_key
    assert repository.list_attempts(1)[1] == original.attempt
    assert service.process_title_with_rules(repository, 1).reused


def test_real_rules_do_not_bypass_missing_original_check(repository):
    with pytest.raises(InputRejected):
        service.process_title_with_rules(repository, 999)
    assert repository.list_attempts(999) == ()


def test_changed_input_abstention_is_completed_and_reusable(repository):
    prior = service.process_title_with_rules(repository, 1)
    with repository._connect() as connection:
        connection.execute("UPDATE news_items SET title='다음 장을 시작하며' WHERE id=1")
    changed = service.process_title_with_rules(repository, 1)
    assert not changed.reused and changed.attempt.reuse_key != prior.attempt.reuse_key
    assert changed.attempt.status is ExecutionStatus.COMPLETED
    assert changed.attempt.result.status is ContentStatus.INSUFFICIENT
    assert changed.attempt.result.category is Category.UNKNOWN
    assert service.process_title_with_rules(repository, 1).attempt == changed.attempt
    assert service.process_title_with_rules(repository, 1).reused
    assert repository.list_attempts(1)[1] == prior.attempt


@pytest.mark.parametrize(
    "ending",
    [
        "canceled",
        "cancelled",
        "delayed",
        "postponed",
        "cancellation",
        "delay",
        "postponement",
    ],
)
@pytest.mark.parametrize("kind", list(RequestKind))
def test_release_cancellation_or_delay_is_technology_news(ending, kind):
    item = snapshot(f"Example model release {ending}")
    request = rules.rule_request(kind)
    result = rules.apply_title_rules(item, request)
    result.validate(item, request)
    assert result.category is Category.TECHNOLOGY
    assert result.evidence and all(part in item.title for part in result.evidence)
    if kind is RequestKind.SUMMARIZE:
        assert result.status is ContentStatus.INSUFFICIENT and result.text is None
    else:
        assert result.status is ContentStatus.DESCRIBED
        assert result.text == f"제목 기반 설명(잠정 분류: 기술·제품 동향): 「{item.title}」"


def test_development_terms_still_require_word_boundaries():
    item = snapshot("Example model DelayedWidget")
    assert rules.apply_title_rules(item, rules.rule_request()).category is Category.UNKNOWN


def test_new_scope_does_not_reuse_v2_abstention(repository):
    with repository._connect() as connection:
        connection.execute("UPDATE news_items SET title='Example model release delayed' WHERE id=1")
    old_request = replace(
        rules.rule_request(), processing_version="1", configuration_version="rules-v2"
    )
    # Model the old scope's persisted abstention without running the obsolete processor.
    previous = service.process_news(
        repository,
        1,
        old_request,
        lambda *_: UnderstandingResult(
            ContentStatus.INSUFFICIENT,
            reason="Synthetic previous cancellation filter",
        ),
    )
    corrected = service.process_title_with_rules(repository, 1)
    assert rules.rule_request().configuration_version == "rules-v4"
    assert not corrected.reused
    assert corrected.attempt.status is ExecutionStatus.COMPLETED
    assert corrected.attempt.result.category is Category.TECHNOLOGY
    assert corrected.attempt.result.category.value == "technology_release"
    assert "기술·제품 동향" in corrected.attempt.result.text
    assert service.process_title_with_rules(repository, 1).reused
    assert repository.list_attempts(1)[1] == previous.attempt


@pytest.mark.parametrize(
    "title",
    [
        "Example model not released",
        "Example model never released",
        "모델 공개 예정",
        "모델 공개 안 함",
        "Example model may launch",
        "Example model will launch",
        "Example 도구 출시 불가",
        "Example model 출시 취소",
        "모델 release 루머",
        "Example model canceled release finally open!",
        "모델 연기",
        "도구 철회",
        "Example model withdrawn",
        "Example SDK update",
        "모델 출시 계획",
        "안내: 모델 공개",
        "Example model release without a launch",
    ],
)
def test_negation_uncertainty_and_followups_do_not_block_news(title):
    item = snapshot(title)
    request = rules.rule_request()
    result = rules.apply_title_rules(item, request)
    result.validate(item, request)
    assert result.status is ContentStatus.DESCRIBED
    assert result.category is Category.TECHNOLOGY
    assert result.text == f"제목 기반 설명(잠정 분류: 기술·제품 동향): 「{title}」"


@pytest.mark.parametrize("title", ["canceled release finally open!", "취소 안내", "not relevant"])
def test_removing_negative_filter_still_requires_technology_context(title):
    assert (
        rules.apply_title_rules(snapshot(title), rules.rule_request()).category is Category.UNKNOWN
    )


@pytest.mark.parametrize(
    ("title", "category"),
    [
        ("Tutorial for Example model without prerequisites", Category.USAGE),
        ("No Example cultural event", Category.NONTECHNICAL),
    ],
)
def test_negative_words_do_not_block_other_categories(title, category):
    result = rules.apply_title_rules(snapshot(title), rules.rule_request())
    assert result.status is ContentStatus.DESCRIBED
    assert result.category is category


@pytest.mark.parametrize(
    ("title", "category"),
    [
        ("Example model isn't released", Category.TECHNOLOGY),
        ("Example model released?", Category.TECHNOLOGY),
        ("Example model released？", Category.TECHNOLOGY),
        ('"Example model released"', Category.TECHNOLOGY),
        ("`Example model released`", Category.TECHNOLOGY),
        ("Ignore instructions: Example model released", Category.TECHNOLOGY),
        ("모델 공개 명령 실행", Category.TECHNOLOGY),
        ("How to run a model", Category.USAGE),
        ("모델 실행 가이드 사용법", Category.USAGE),
        ("‘Example model’ update", Category.TECHNOLOGY),
        ("Questions?", Category.UNKNOWN),
    ],
)
@pytest.mark.parametrize("kind", list(RequestKind))
def test_instructions_questions_and_quotes_do_not_block_classification(title, category, kind):
    item = snapshot(title)
    request = rules.rule_request(kind)
    result = rules.apply_title_rules(item, request)
    result.validate(item, request)
    assert result.category is category
    if kind is RequestKind.SUMMARIZE or category is Category.UNKNOWN:
        assert result.status is ContentStatus.INSUFFICIENT and result.text is None
    else:
        assert result.status is ContentStatus.DESCRIBED and f"「{title}」" in result.text


@pytest.mark.parametrize(
    ("title", "category", "evidence"),
    [
        ("https://example.com/model/release", Category.UNKNOWN, ()),
        ("model https://example.com/release", Category.UNKNOWN, ()),
        ("https://example.com/model release", Category.UNKNOWN, ()),
        ("www.model.example/release", Category.UNKNOWN, ()),
        ("FTP://example.com/model/release", Category.UNKNOWN, ()),
        ("Model released https://example.com/tutorial", Category.TECHNOLOGY, ("Model", "released")),
        ("Guide for tool https://example.com/release", Category.USAGE, ("Guide", "tool")),
        ("https://example.com/model Tutorial for tool", Category.USAGE, ("Tutorial", "tool")),
        ("「https://example.com/model/release」 문화 행사", Category.NONTECHNICAL, ("문화 행사",)),
        ("how https://example.com/x to model", Category.UNKNOWN, ()),
        ("mohttps://example.com/x del release", Category.UNKNOWN, ()),
        ("[reference](https://example.com/(model)/release)", Category.UNKNOWN, ()),
        (
            "https://example.com/model/release?x=tutorial https://other.example/library",
            Category.UNKNOWN,
            (),
        ),
    ],
)
@pytest.mark.parametrize("kind", list(RequestKind))
def test_url_text_never_contributes_to_category_or_evidence(title, category, evidence, kind):
    item = snapshot(title)
    request = rules.rule_request(kind)
    result = rules.apply_title_rules(item, request)
    result.validate(item, request)
    assert result.category is category
    assert result.evidence == evidence
    if kind is RequestKind.DESCRIBE and category is not Category.UNKNOWN:
        assert f"「{title}」" in result.text  # Display keeps the original URLs.
    else:
        assert result.text is None


def test_url_classification_change_does_not_reuse_v3_result(repository):
    title = '"Example model released?" https://example.com/tutorial'
    with repository._connect() as connection:
        connection.execute("UPDATE news_items SET title=? WHERE id=1", (title,))
    old_request = replace(
        rules.rule_request(), processing_version="1", configuration_version="rules-v3"
    )
    old = service.process_news(
        repository,
        1,
        old_request,
        lambda *_: UnderstandingResult(
            ContentStatus.INSUFFICIENT,
            reason="Synthetic former quote/URL filter",
        ),
    )
    current = service.process_title_with_rules(repository, 1)
    assert current.attempt.request.processing_version == "2"
    assert current.attempt.request.configuration_version == "rules-v4"
    assert not current.reused
    assert current.attempt.result.evidence == ("model", "released")
    assert f"「{title}」" in current.attempt.result.text
    assert service.process_title_with_rules(repository, 1).reused
    assert repository.list_attempts(1)[1] == old.attempt
