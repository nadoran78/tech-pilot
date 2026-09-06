# News Collection Architecture

- **Status:** Draft
- **Applies to:** Phase 3
- **Purpose:** 뉴스 수집 MVP의 컴포넌트 경계, 데이터 흐름과 실패 격리 원칙을 정의한다.
- **Read when:** 수집기, 출처 어댑터, 저장소 또는 CLI를 구현·검토할 때
- **Related documents:** [3단계 문서](../phases/03-news-collection.md), [뉴스 항목 계약](../specs/news-item.md), [출처·근거 정책](../policies/source-and-evidence.md), [기술 스택](tech-stack.md)

## Scope

이 문서는 첫 수집 MVP의 논리적 경계를 정의한다. SQLite 테이블·migration, 실제 HTTP 요청, CLI 하위 명령과 자동 실행 방식은 후속 구현 Issue에서 결정한다.

## Proposed Flow

```text
CLI collect command
  → collection coordinator
  → source adapter (one per approved source)
  → normalized source observation
  → identity and duplicate check
  → news repository
  → collection result summary
```

1. CLI는 명시적으로 수집을 시작하고 결과 요약을 표시한다.
2. 수집 조정자는 승인된 출처를 독립적으로 순회하며, 한 출처의 실패가 다른 출처의 처리를 중단시키지 않게 한다.
3. 출처 어댑터는 RSS·Atom, 공식 API 또는 승인된 HTML 접근 중 하나를 사용해 원본 응답을 읽고, 출처 고유 필드를 관찰 결과로 변환한다.
4. 정규화 단계는 [뉴스 항목 계약](../specs/news-item.md)의 공통 필드와 원본 근거를 만든다.
5. 식별·중복 검사 단계는 외부 ID와 정규화한 대표 URL을 사용해 새 항목·기존 항목·검토 필요 항목을 구분한다.
6. 저장소는 뉴스 항목, 출처 관찰 결과와 수집 실행 결과를 분리해 보관한다.

## Component Responsibilities

| 컴포넌트 | 책임 | 하지 않는 일 |
|---|---|---|
| CLI | 수동 실행 진입점, 옵션 검증, 사람에게 읽을 수 있는 결과 표시 | 수집 규칙과 저장 세부 구현 |
| Collection coordinator | 출처 순회, 결과 집계, 실패 격리 | RSS·API·HTML 형식 해석 |
| Source adapter | 출처 접근, 응답 해석, 원본 필드 보존 | 전역 중복 판단, 저장소 직접 제어 |
| Normalizer | 출처별 관찰 결과를 공통 뉴스 항목 계약으로 변환 | 생성 요약·개인 영향 판단 |
| Identity and duplicate check | 외부 ID·대표 URL로 기술적 중복 판정 | 콘텐츠 의미 유사성 판단 |
| News repository | 뉴스 항목·관찰 결과·수집 실행 결과의 영속화 | HTTP 요청·출처 정책 판정 |

## Source Adapter Boundary

각 어댑터는 다음 입력과 결과를 논리적으로 제공한다.

- 입력: 승인된 `source_id`, 접근 URL, 이전 수집의 HTTP validator(있다면), 요청 제한 설정
- 성공 결과: 원본 응답 메타데이터와 하나 이상의 출처 관찰 결과
- 변경 없음: 조건부 요청이 지원되고 변경이 없음을 응답한 경우
- 실패 결과: 출처 식별자, 실패 단계, 재시도 가능성 판단에 필요한 안전한 오류 정보

요청 시 timeout, `ETag`와 `Last-Modified`의 사용 여부는 출처별 설정으로 남긴다. 응답이 validator를 제공하면 이후 요청에서 조건부 요청을 사용할 수 있으며, 304 응답은 새 항목을 만들지 않는다. 이 원칙은 HTTP의 validator·조건부 요청 의미를 따른다. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)

## Failure and Evidence Boundaries

- 한 출처의 접근·파싱 실패는 수집 실행 결과에 기록하고 다른 출처의 처리를 계속한다.
- 파싱할 수 없는 항목, 안정적인 식별자·대표 URL이 없는 항목은 자동 저장하지 않고 출처 품질 문제로 기록한다.
- 원본 응답에서 관찰한 값과 이후 단계가 생성한 값은 같은 필드에 섞지 않는다.
- 원본 문서 전체의 보관 범위, 재시도 횟수, timeout 값과 실행 잠금은 구현 전 별도 결정이 필요하다.

## Deferred Decisions

- 초기 승인 출처 목록과 출처별 접근 URL
- SQLite schema와 migration 순서
- URL 정규화의 출처별 예외와 콘텐츠 hash 사용 여부
- timeout·재시도·backoff·실행 잠금의 구체적 값
- 수집 실행 결과의 보존 기간과 운영 runbook
