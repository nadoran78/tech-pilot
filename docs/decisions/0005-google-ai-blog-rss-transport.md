# 0005: Google AI Blog RSS 수동 수집 전송

- **Status:** Accepted
- **Date:** 2026-09-27
- **Phase:** 3
- **Purpose:** Google AI Blog RSS의 제한적 수동 수집에 적용하는 HTTP 요청과 요청 제한의 경계를 정의한다.
- **Read when:** Google AI Blog RSS adapter, 출처별 요청 제한 또는 수동 `collect` 흐름을 구현·검토할 때
- **Related documents:** [Google AI Blog RSS 출처](../sources/google-ai-blog-rss.md), [출처·근거 정책](../policies/source-and-evidence.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [뉴스 항목 계약](../specs/news-item.md), [0004: Hugging Face RSS 수집 전송](0004-hugging-face-rss-transport.md)

## Context

Google AI Blog RSS는 2026-09-27에 사용자가 제한적 운영을 승인한 출처다. 승인 범위는 개인용 로컬 SQLite의 최소 메타데이터 보관과 하루 1회 이하의 수동 요청이며, 자동 재시도·backoff·scheduler·외부 제공은 포함하지 않는다.

이 결정 작성 당시에는 실제 HTTP 전송 조건과 하루 1회 제한의 판정 방식이 정해져 있지 않았고, 수집 구현도 Hugging Face RSS만 지원했다. 관찰한 응답에는 `ETag`, `Last-Modified`, `RateLimit`, `Retry-After`가 없었으므로 Hugging Face RSS의 conditional HTTP 동작을 그대로 적용할 수 없었다.

## Facts and Constraints

다음은 출처 조사와 기존 승인에서 확인된 사실·제약이다.

- 표준 endpoint는 `https://blog.google/innovation-and-ai/technology/ai/rss/`다. 이전 경로는 이 주소로 redirect됐지만, endpoint의 지속성은 보장되지 않는다.
- RSS는 익명 요청으로 XML을 반환했고, 표본에서는 `id`, `title`, `link`, `published`, `updated`를 읽을 수 있었다.
- 뉴스 항목에는 `id`, 제목, 원문 URL, 발표 시각과 수집 시각만 보관한다. `updated`, 원문 전문, 이미지, 첨부 파일은 보관하지 않는다.
- 제공자가 공개한 요청 빈도·timeout·재시도 정책은 이 조사 범위에서 확인하지 못했다. 아래 값은 제공자의 보장이 아니라 프로젝트의 보수적인 운영 제안이다.

## Decision

사용자가 2026-09-27에 아래 전송 및 요청 제한 기준을 승인했다.

### HTTP Request

- Google AI Blog RSS adapter는 위 표준 endpoint에 GET 요청을 한 번만 보낸다.
- 요청 timeout은 10초, User-Agent는 `tech-pilot/0.1 (personal news collector)`다. Hugging Face 수집의 초기 보수적 기본값과 맞춰 수동 운영을 일관되게 시작한다.
- 자동 retry, backoff, scheduler는 사용하지 않는다. 오류가 나면 결과를 보고 사용자가 별도 수동 실행을 결정한다.
- `ETag`와 `Last-Modified`를 관찰하지 못했으므로 validator를 저장하거나 `If-None-Match`, `If-Modified-Since` 요청 header를 보내지 않는다. 이후 응답 계약이 바뀌면 출처 기록과 이 결정을 다시 검토한다.
- 2xx 응답이면서 RSS를 신뢰할 수 있게 파싱한 경우에만 뉴스 항목을 저장한다. HTTP 오류, timeout, XML 파싱 오류, 필수 필드가 없는 항목은 성공으로 취급하거나 부분 데이터를 저장하지 않는다.

### Daily Request Limit

- 하루 1회 이하는 **KST(`Asia/Seoul`) 달력 날짜**의 00:00:00부터 다음 00:00:00 직전까지 출처별 요청을 최대 한 번 보내는 것으로 정의한다.
- 다음 구현은 HTTP 요청 전에 짧은 SQLite 트랜잭션으로 해당 날짜의 출처별 요청 시도를 **원자적으로 예약**해야 한다. `(source_id, KST 날짜)` 유일 제약 또는 동등한 `INSERT ... ON CONFLICT` 기반 예약을 사용하며, 예약에 성공한 실행만 HTTP 요청을 보낸다. 이미 예약된 경우에는 HTTP 요청을 보내지 않고 제한 초과 결과로 종료한다.
- 예약에는 `source_id`, KST 날짜 또는 그 날짜를 판정할 수 있는 시각, 시도 시작 시각을 보관한다. 전송 뒤 timeout·HTTP 오류·파싱 오류가 나거나 프로세스가 종료돼도 예약은 남아 그 시도를 하루 한 번에 포함한다.
- 뉴스 항목·HTTP validator 상태와 이 요청 예약 상태는 서로 다른 책임으로 다룬다.

이 해석은 사용자가 이해하기 쉬운 일일 한도를 우선한다. 자정 전후에 두 요청이 가까워질 수 있으나, 자동 실행이 아닌 수동 수집과 하루 한 번의 좁은 승인 범위에서는 운영자가 확인하기 쉽다는 장점이 있다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| KST 달력 날짜별 한 번, 실패 시도 포함 | 사용자에게 명확한 하루 한도이고 실패 때 반복 요청하는 경로를 막는다. 채택한 선택이다. |
| 최근 성공 시점부터 24시간 간격 | 자정 경계의 가까운 두 요청을 피할 수 있지만, 실패 시도·마지막 성공 시점의 해석이 복잡해지고 한국 시간의 일일 운영 기준과도 다르다. |
| 실패 시도는 한도에서 제외 | 일시적 오류 뒤 재시도 기회를 준다. 그러나 오류가 반복될 때 승인 범위보다 많은 요청을 보낼 수 있다. |
| Hugging Face와 동일하게 conditional HTTP 사용 | 변경 없는 응답 전송을 줄일 수 있지만, 현재 Google 응답에서 사용할 validator가 관찰되지 않았다. |

## Consequences

- 장점: 제공자 요청 빈도 정보가 없는 상황에서도 수동·저빈도·최소 보관이라는 승인 범위를 코드로 검증할 수 있다.
- 비용: 하루의 첫 요청이 실패해도 같은 KST 날짜에는 자동 또는 추가 수동 요청을 하지 못한다. 사용자는 다음 날 다시 실행해야 한다.
- 비용: 자정 직전과 직후의 두 수동 요청은 시간상 가깝게 발생할 수 있다. 더 엄격한 간격이 필요해지면 rolling 24시간 정책을 별도 결정으로 검토한다.
- 구현 상태: Issue #39에서 원자적 요청 예약 저장소를, Issue #41에서 Google 정규화 모듈·fetcher·수집 함수·synthetic fixture·수집 요약과 요청 제한 연결을 추가했다. mock HTTP 테스트에서 실패 후 예약 유지와 동시 실행 시 단일 요청을 검증했다.
- CLI 연결: Issue #43에서 다중 출처 coordinator와 출처 선택 옵션을 추가하고, 한 출처의 실패나 요청 제한 도달 뒤에도 다른 출처의 실행이 계속됨을 mock 테스트로 검증했다. 실제 Google 수집과 품질 검토는 아직 수행하지 않았다.
