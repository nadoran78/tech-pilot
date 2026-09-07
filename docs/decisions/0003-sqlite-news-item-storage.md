# 0003: SQLite News Item Storage

- **Status:** Accepted
- **Date:** 2026-09-07
- **Phase:** 3
- **Purpose:** 뉴스 항목 계약을 로컬 SQLite에 어떤 최소 단위와 중복 규칙으로 보관할지 제안한다.
- **Read when:** 뉴스 저장·조회, migration 또는 중복 판정을 구현하거나 검토할 때
- **Related documents:** [뉴스 항목 계약](../specs/news-item.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [0001: 뉴스 수집 MVP 기술 스택](0001-news-collection-mvp-tech-stack.md)

## Context

승인된 뉴스 항목 계약은 보관 필드와 기술적 중복 기준을 정의하지만, 실제 SQLite 테이블과 migration 경계는 아직 정하지 않았다. 첫 출처를 연결하기 전에 네트워크와 무관하게 이 계약을 검증할 수 있는 저장 기반이 필요하다.

## Decision

초기 구현은 명시적 SQL migration으로 `schema_migrations`와 `news_items`만 만든다.

- 각 migration의 SQL과 버전·적용 시각 기록은 하나의 SQLite savepoint로 원자적으로 적용한다.
- `news_items`는 뉴스 항목 계약의 필수 필드, 선택 필드, 근거 URL과 수집 시각을 보관한다.
- `(source_id, external_id)`는 external ID가 있을 때만 고유하며, `canonical_url`은 전역적으로 고유하다.
- 저장 전에 두 기술적 식별자를 각각 조회한다. 하나만 일치하면 중복으로 반환하고, 서로 다른 기존 항목을 가리키면 어떤 항목도 변경하지 않고 `review_required`를 반환한다.
- canonical URL은 공통으로 안전한 fragment 제거만 수행한다. 추적 파라미터 제거는 출처별 규칙이 마련될 때까지 보류한다.
- 수집 시각은 UTC ISO 8601 문자열로 저장한다. 원문 게시 시각은 시간대 정보를 가진 ISO 8601과 원문 문자열을 함께 보관한다.

`collection_runs`와 `source_observations` 테이블은 coordinator가 실제 관측 데이터를 만들 때 별도 migration으로 추가한다.

사용자가 2026-09-07에 이 결정을 명시적으로 승인했고, 구현은 [PR #14](https://github.com/nadoran78/tech-pilot/pull/14)로 `develop`에 병합됐다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| 초기에는 뉴스 항목만 저장 | 계약과 중복 규칙을 작은 단위로 검증하고, 수집 흐름이 생긴 뒤 관측·실행 이력을 실제 요구에 맞춰 설계할 수 있다. 제안한 선택이다. |
| 처음부터 실행·관측·항목 테이블을 모두 추가 | 장기 구조를 미리 표현할 수 있지만, 아직 없는 coordinator의 데이터 수명과 오류 모델을 추측하게 된다. |
| ORM을 도입 | schema 표현은 편해질 수 있으나, 승인된 stdlib SQLite와 명시적 SQL migration 기준에 새 의존성과 추상화를 더한다. |

## Consequences

- 장점: migration 이력, 저장 계약, 중복 보류 동작을 외부 네트워크 없이 테스트할 수 있다.
- 비용: 실행 이력과 원본 관측값은 다음 수집 흐름 작업 전까지 저장하지 않는다.
- 후속 작업: 첫 source adapter와 coordinator를 구현할 때 관측·실행 이력의 관계와 migration을 추가로 검토한다.
