# News Collection Architecture

- **Status:** Accepted
- **Applies to:** Phase 3
- **Purpose:** 뉴스 수집 MVP의 컴포넌트 경계, 데이터 흐름과 실패 격리 원칙을 정의한다.
- **Read when:** 수집기, 출처 어댑터, 저장소 또는 CLI를 구현·검토할 때
- **Related documents:** [3단계 문서](../phases/03-news-collection.md), [뉴스 항목 계약](../specs/news-item.md), [출처·근거 정책](../policies/source-and-evidence.md), [기술 스택](tech-stack.md)

## Scope

이 문서는 첫 수집 MVP의 논리적 경계를 정의한다. SQLite 테이블·migration은 [0003: SQLite 뉴스 항목 저장](../decisions/0003-sqlite-news-item-storage.md)에서, 첫 Hugging Face RSS의 HTTP 요청·CLI 경계는 [0004: Hugging Face RSS 수집 전송](../decisions/0004-hugging-face-rss-transport.md)에서 관리한다. 다른 출처와 자동 실행 방식은 후속 구현 Issue에서 결정한다.

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

## Source Registry Implementation

Issue #57에서는 [registry](../../src/tech_pilot/collection/registry.py)에 승인된 출처 ID와 `(SQLiteNewsRepository, httpx.Client) -> CollectionSummary` callable을 등록한다. 목록은 구성 시 검증한 순서 있는 스냅샷이며 중복·빈 ID를 거부한다. 실행 중 전역 등록 목록을 변경하거나 설정 파일·동적 plugin을 로드하지 않는다.

출처를 추가할 때는 다음 순서로 진행한다.

1. [출처·근거 정책](../policies/source-and-evidence.md)에 따라 운영 승인을 받는다. 코드 등록 자체는 승인이 아니다.
2. 전용 정규화·수집 모듈과 네트워크 없는 테스트를 만든다. 요청 제한·timeout·validator 정책은 해당 수집기에 둔다.
3. 공통 호출 형태로 연결하는 wrapper와 운영 registry 항목을 추가한다. 결과의 source_id는 등록 ID와 일치해야 한다.
4. coordinator·CLI에 출처별 분기를 추가하지 않고 실행·이력·실패 격리와 기존 출처 회귀를 검증한다.

coordinator는 전체 선택을 부작용 전에 검증하고 registry callable을 순차 호출한다. 선택 중복은 최초 선택 순서를 유지해 제거한다. CLI 허용 목록과 기본 실행 순서는 운영 registry에서 도출한다. 테스트는 별도 registry를 주입하며 운영 CLI에 가짜 출처를 노출하지 않는다. 결과 ID 불일치는 안전한 로컬 실패로 처리한다.

공통 실패·이력 규칙은 기존 계약을 유지한다. [registry 테스트](../../tests/test_source_registry.py)는 가짜 출처의 성공·실패·잘못된 결과 ID, 등록·선택 검증과 CLI 목록 도출을 확인한다. 실제 새 출처 승인·수집을 수행한 근거는 아니다. PR #56의 종합 판단 갱신은 이 구현의 검증·병합 뒤 별도 작업으로 진행한다.

## Failure and Evidence Boundaries

- 한 출처의 접근·파싱 실패는 수집 실행 결과에 기록하고 다른 출처의 처리를 계속한다.
- 파싱할 수 없는 항목, 안정적인 식별자·대표 URL이 없는 항목은 자동 저장하지 않고 출처 품질 문제로 기록한다.
- 원본 응답에서 관찰한 값과 이후 단계가 생성한 값은 같은 필드에 섞지 않는다.
- 원본 문서 전체의 보관 범위, 재시도 횟수, timeout 값과 실행 잠금은 구현 전 별도 결정이 필요하다.

## Deferred Decisions

- 추가 승인 출처와 출처별 접근 URL
- URL 정규화의 출처별 예외와 콘텐츠 hash 사용 여부
- timeout·재시도·backoff·실행 잠금의 구체적 값
- 수집 실행 결과의 보존 기간과 운영 runbook
