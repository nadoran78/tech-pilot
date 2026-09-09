# 0004: Hugging Face RSS Collection Transport

- **Status:** Proposed
- **Date:** 2026-09-09
- **Phase:** 3
- **Purpose:** 첫 수동 RSS 수집의 HTTP 요청·validator·로컬 DB 기본 경계를 제안한다.
- **Read when:** Hugging Face RSS 요청, 조건부 수집 또는 `collect` CLI를 구현·검토할 때
- **Related documents:** [Hugging Face Blog RSS 출처](../sources/hugging-face-blog-rss.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [0003: SQLite 뉴스 항목 저장](0003-sqlite-news-item-storage.md)

## Context

RSS parser와 뉴스 저장소는 독립적으로 검증됐지만, 실제 수동 수집에서 HTTP 요청을 어떤 제한과 상태로 실행할지는 정해지지 않았다. 출처 기록은 timeout, 요청 간격, conditional HTTP를 adapter 구현에서 결정하도록 남겼다.

## Decision

초기 수동 수집은 다음의 최소 HTTP 경계를 사용한다.

- `tech-pilot collect` 한 번은 Hugging Face Blog RSS endpoint에 GET 요청을 한 번만 보낸다.
- 요청 timeout은 10초이고, user-agent는 `tech-pilot/0.1 (personal news collector)`다.
- 자동 재시도·backoff는 하지 않는다. 사용자는 오류 요약을 확인한 뒤 필요할 때만 다시 실행한다.
- HTTP 2xx 응답 중 RSS가 신뢰할 수 있게 파싱된 경우에만 `ETag`, `Last-Modified`를 출처 ID별 SQLite 상태로 저장하고, 다음 요청에 `If-None-Match`, `If-Modified-Since`로 보낸다.
- 304 응답은 RSS 파싱·뉴스 저장 없이 변경 없음으로 요약한다.
- 기본 DB 경로는 gitignore된 `data/tech-pilot.sqlite3`다. CLI 옵션으로 다른 경로를 지정할 수 있다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| 단일 수동 요청과 conditional HTTP | 첫 실제 수집을 작고 관찰 가능하게 시작하면서 불필요한 재전송을 줄인다. 제안한 선택이다. |
| 매번 무조건 요청 | 구현은 더 단순하지만 feed가 바뀌지 않아도 본문을 다시 전송·파싱한다. |
| scheduler와 재시도까지 동시에 도입 | 자동화에는 유리하지만 실패 정책·잠금·운영 관찰 범위를 크게 늘린다. |

## Consequences

- 장점: 첫 수집 경로가 재실행 가능하며, 304 응답에서는 저장소를 건드리지 않는다.
- 비용: 네트워크 오류는 자동 복구하지 않으며 사용자 재실행이 필요하다.
- 후속 작업: 여러 출처 또는 scheduler를 추가할 때 요청 간격, 재시도, 잠금과 실행 이력을 별도 결정으로 검토한다.
