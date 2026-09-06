# News Item Contract

- **Status:** Draft
- **Applies to:** Phase 3
- **Purpose:** 뉴스 수집 MVP가 보관하는 최소 항목, 원본 근거와 기술적 중복 식별 기준을 정의한다.
- **Read when:** 정규화, 저장소, 출처 어댑터 또는 테스트 fixture를 구현·검토할 때
- **Related documents:** [수집 아키텍처](../architecture/news-collection.md), [출처·근거 정책](../policies/source-and-evidence.md), [3단계 문서](../phases/03-news-collection.md)

## Scope

이 계약은 구현 전의 논리적 데이터 모델이다. SQLite 테이블명, 자료형, index와 migration은 이를 만족하는 후속 저장소 Issue에서 결정한다.

## Logical News Item

| 필드 | 필요 | 의미 | 원본·생성 구분 |
|---|---|---|---|
| `source_id` | 필수 | 승인된 출처를 식별하는 안정적인 내부 이름 | 시스템 설정값 |
| `external_id` | 선택 | 출처가 제공하는 항목의 안정적인 ID | 원본 |
| `canonical_url` | 필수 | 항목을 대표하는 원문 URL | 원본 링크를 바탕으로 시스템이 정규화 |
| `title` | 필수 | 출처가 제공한 항목 제목 | 원본 |
| `published_at` | 선택 | 출처가 제공한 발표·게시 시각 | 원본 |
| `published_at_raw` | 선택 | 파싱 전 원본 시각 값 | 원본 |
| `collected_at` | 필수 | Tech Pilot이 항목을 관찰한 UTC 시각 | 시스템 관찰값 |
| `evidence_url` | 필수 | 항목 사실을 다시 확인할 수 있는 원문 또는 공식 발표 URL | 원본 |
| `source_endpoint` | 필수 | 항목을 발견한 RSS·Atom feed 또는 API endpoint | 시스템 관찰값 |
| `excerpt` | 선택 | 출처가 제공한 짧은 설명·요약 | 원본 |
| `raw_metadata` | 선택 | 이후 재해석에 필요한 출처 고유 값의 제한된 보존 영역 | 원본 |

`canonical_url`과 `evidence_url`은 보통 같지만, feed의 링크가 중계 URL이고 공식 원문 URL을 확인할 수 있는 경우에는 다를 수 있다. 생성 요약, 분류, 개인 연관성 평가는 이 계약에 포함하지 않으며 이후 단계에서 별도 데이터로 보관한다.

## Time Semantics

- `published_at`은 출처가 명시한 시각만 기록한다. 알 수 없거나 신뢰할 수 없으면 비워 둔다.
- `collected_at`은 항상 UTC로 기록하며, 발표 시각을 추정해 대체하지 않는다.
- 시각 정밀도·timezone이 불완전한 값은 `published_at_raw`를 보존하고, 정규화 실패를 조용히 현재 시각으로 바꾸지 않는다.

Atom entry는 안정적인 `id`와 `updated`를 제공할 수 있으며, `id`는 항목의 영속적 고유 식별자를 표현한다. 다만 출처 간 ID 충돌을 막기 위해 `source_id` 없이 사용하지 않는다. [RFC 4287](https://www.rfc-editor.org/rfc/rfc4287/)

## Technical Duplicate Rules

중복 판단은 같은 기술적 항목을 반복 저장하지 않기 위한 것이며, 서로 다른 기사·발표의 의미상 동일 사건을 통합하지 않는다.

1. 같은 `source_id`와 동일한 비어 있지 않은 `external_id`는 같은 항목으로 본다.
2. 외부 ID가 없거나 일치하지 않으면, 정규화한 동일 `canonical_url`은 같은 항목으로 본다.
3. URL fragment는 제거한다. 추적 query parameter의 제거는 출처별로 안전성이 확인된 경우에만 적용한다.
4. 두 기준이 모두 없거나 서로 충돌하면 자동 병합하지 않고 검토 필요 결과로 기록한다.
5. 제목·시각·본문 hash만으로 자동 중복 판단하지 않는다. 콘텐츠 기반 중복은 별도 설계와 fixture 검증 후 추가한다.

## Validation Rules

- 필수 필드가 비어 있거나 `canonical_url`이 절대 URL이 아니면 항목을 저장하지 않는다.
- `evidence_url`은 접근한 출처·원문과의 관계를 확인할 수 있어야 한다.
- HTML·XHTML 성격의 excerpt는 실행·표시 전에 안전하게 다뤄야 하며, 원본 markup을 생성 요약으로 오인하지 않는다.
- 수집기는 동일 입력을 다시 처리해도 위 식별 기준 아래 새 뉴스 항목을 만들지 않아야 한다.

## Deferred Decisions

- 내부 primary key와 출처 관찰 결과의 별도 테이블 구조
- 원문 전문·첨부 파일의 보관 범위와 라이선스 처리
- 콘텐츠 hash의 계산 위치와 알고리즘
- 의미 기반 사건 통합과 생성 요약의 데이터 계약
