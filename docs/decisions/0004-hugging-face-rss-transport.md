# 0004: Hugging Face RSS Collection Transport

- **Status:** Proposed
- **Date:** 2026-09-09
- **Phase:** 3
- **Purpose:** 첫 수동 RSS 수집의 HTTP 요청·validator·로컬 DB 기본 경계를 제안한다.
- **Read when:** Hugging Face RSS 요청, 조건부 수집 또는 `collect` CLI를 구현·검토할 때
- **Related documents:** [Hugging Face Blog RSS 출처](../sources/hugging-face-blog-rss.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [0003: SQLite 뉴스 항목 저장](0003-sqlite-news-item-storage.md)

## Context

2026-09-09 초기 제안 당시에는 RSS parser와 뉴스 저장소가 독립적으로 검증됐지만, 실제 수동 수집의 HTTP 경계는 정해지지 않았다. 이후 수동 수집·다중 출처·registry·실행 이력이 구현됐다. 2026-10-15 Issue #59에서 develop `491a0a5`의 구현과 이 문서를 대조했다. 이는 설명의 정합성 정리이며 전송 정책 변경이나 ADR 승인이 아니다. 사용자 명시적 승인 전까지 Proposed를 유지한다.

## Decision

초기 수동 수집은 다음의 최소 HTTP 경계를 사용한다.

- Hugging Face가 선택된 `tech-pilot collect` 실행은 해당 RSS endpoint에 GET 요청을 최대 한 번 보낸다. 출처가 선택되지 않았거나 실행 이력 시작 기록에 실패하면 요청하지 않는다. 기본 출처 선택은 현재 registry를 따르며, 이 문서가 다른 출처의 전송 정책을 정의하지는 않는다.
- 요청 timeout은 10초이고, user-agent는 `tech-pilot/0.1 (personal news collector)`다.
- 자동 재시도·backoff는 하지 않는다. 사용자는 오류 요약을 확인한 뒤 필요할 때만 다시 실행한다.
- HTTP 2xx 응답은 RSS 파싱과 항목 처리 완료 후 응답의 `ETag`, `Last-Modified`를 출처 ID별 SQLite 상태에 반영한다. 응답에 두 값이 모두 없으면 기존 validator를 삭제한다. HTTP 요청·상태 오류 또는 RSS 파싱 실패 때는 validator를 반영하지 않는다.
- 이전 validator의 존재하는 값을 다음 요청의 `If-None-Match`, `If-Modified-Since`로 보낸다.
- 304 응답은 RSS 파싱·뉴스 항목 저장 없이 `unchanged`로 요약한다. 단, 응답에 validator 값이 하나라도 있으면 해당 응답 값으로 validator 행을 저장하고 `updated_at`을 갱신한다. 이때 응답에 없는 다른 필드는 이전 값과 병합하지 않고 NULL로 대체될 수 있다. 두 값 모두 없으면 기존 행을 유지한다. `updated_at`은 뉴스 발표·최초 수집 시각이 아니다.
- 기본 DB 경로는 gitignore된 `data/tech-pilot.sqlite3`다. CLI 옵션으로 다른 경로를 지정할 수 있다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| 단일 수동 요청과 conditional HTTP | 첫 실제 수집을 작고 관찰 가능하게 시작하면서 불필요한 재전송을 줄인다. 제안한 선택이다. |
| 매번 무조건 요청 | 구현은 더 단순하지만 feed가 바뀌지 않아도 본문을 다시 전송·파싱한다. |
| scheduler와 재시도까지 동시에 도입 | 자동화에는 유리하지만 실패 정책·잠금·운영 관찰 범위를 크게 늘린다. |

## Consequences

- 장점: 수동 수집 경로가 재실행 가능하며, 304 응답에서는 RSS 파싱·뉴스 항목 저장을 생략한다. validator 상태와 실행 이력까지 쓰기 없이 유지한다는 뜻은 아니다.
- 비용: 네트워크 오류는 자동 복구하지 않으며 사용자 재실행이 필요하다.
- 후속 작업: scheduler 도입 시 출처별 접근 승인, 요청 간격·재시도·잠금·운영 정책은 별도 검토한다. 현재의 수동 승인 범위를 자동 실행 승인으로 확장하지 않는다.

## Current Implementation and Evidence

- [수집 구현](../../src/tech_pilot/collection/hugging_face_blog.py)과 [validator 저장소](../../src/tech_pilot/storage/repository.py)가 위 상태 반영의 코드 근거다. timeout은 HTTPX 요청에 10초를 전달하며 전체 명령의 총 실행 시간 상한을 뜻하지 않는다.
- [조건부 수집 테스트](../../tests/test_hugging_face_collection.py)는 최초 저장·조건부 header·validator 없는 304의 뉴스 미추가·HTTP 오류·파싱 실패 후 validator 미저장을 확인한다. 304 응답의 일부 validator 필드 대체 조합을 이 테스트에서 모두 검증한 것은 아니며 해당 설명은 코드 대조 근거다.
- 다중 출처 순회·실패 격리·등록 절차는 [수집 아키텍처](../architecture/news-collection.md), Google의 별도 요청 정책은 [ADR 0005](0005-google-ai-blog-rss-transport.md)를 따른다.
- 일반 CLI는 coordinator를 거치므로 304에서도 [ADR 0006](0006-collection-run-history.md)에 따라 시작·완료 이력을 기록한다. [이력 테스트](../../tests/test_collection_history.py)에서 상태 전이와 기록 오류를 검증한다. 출처 수집 함수를 직접 호출하는 것만으로 실행 이력이 생기지는 않는다.
- [2026-10-11 운영 검증](../runbooks/2026-10-11-history-runtime-verification.md)에서는 실제 304, 뉴스 미추가, validator 값 유지·확인 시각 갱신과 완료 이력을 관찰했다. 한 시점의 결과로 장기 응답·모든 validator 조합·장애 처리를 보장하지 않는다.

Issue #59는 코드·정책·접근 승인 범위를 변경하지 않고 설명과 근거를 정리했다. 이 문서의 Proposed 승인 여부, [종합 검토](../phases/03-news-collection-review.md)의 품질 판단 및 4단계 전환은 각각 별도의 사용자 결정이다.
