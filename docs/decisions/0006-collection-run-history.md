# 0006: 수집 실행 이력과 보존 정책

- **Status:** Accepted
- **Date:** 2026-10-10
- **Phase:** 3
- **Purpose:** 출처별 수집 실행 결과의 의미와 초기 보존 정책을 정의한다.
- **Read when:** 실행 이력 저장소, coordinator 기록 또는 history CLI를 구현·검토할 때
- **Related documents:** [수집 아키텍처](../architecture/news-collection.md), [수동 운영](../runbooks/news-collection.md), [뉴스 항목 계약](../specs/news-item.md), [Google 요청 제한](0005-google-ai-blog-rss-transport.md)

## Context

현재 coordinator는 출처별 결과를 CLI에 반환하지만 실행 이력을 영속화하지 않는다. 뉴스 항목의 collected_at은 최초 저장 시각이고, Google 요청 예약은 일일 상한을 강제하는 상태다. 어느 것도 과거 실행의 성공·실패 이력을 대신하지 않는다. 사용자가 2026-10-10에 이 계약과 보존 정책을 명시적으로 승인했다. 구현은 별도 Issue에서 진행한다.

## Decision

### Record Boundary

선택한 출처별 호출 한 번을 한 이력으로 보관한다. 다중 출처 명령은 출처 수만큼 이력을 만든다. 동일 명령을 묶는 상위 실행 ID와 항목별 재관찰 이력은 후속 범위다.

| 필드 | 의미·제약 |
|---|---|
| run_id | 로컬 SQLite가 부여하는 유일한 실행 식별자 |
| source_id | 호출할 승인 출처 식별자 |
| started_at | coordinator가 해당 출처 처리를 시작한 UTC 시각 |
| finished_at | 결과 확정 UTC 시각, running 상태에서는 NULL |
| status | running 또는 기존 completed / unchanged / failed / limit_reached |
| http_status | 관찰한 HTTP 상태, 요청 미전송·응답 미수신이면 NULL |
| inserted / duplicates / review_required / skipped | 확정된 집계, 0 이상; 미확정이면 NULL |
| error_code | request_failed / http_failed / parse_failed / local_failed 중 안전한 분류 또는 NULL |

응답 본문·header·자유 형식 예외 문자열·경로·비밀 값은 저장하지 않는다. 상세 스택 로그를 이력에 복사하지 않는다. completed의 집계는 수집 요약과 일치해야 한다. unchanged·limit_reached는 항목 처리를 하지 않으므로 집계는 0이다. failed는 부분 저장 여부를 현재 요약에서 확정할 수 없으므로 집계를 NULL로 남겨 0개 처리로 오인하지 않게 한다.

### Lifecycle and Failure

1. coordinator가 출처 호출 전에 running 이력을 짧은 트랜잭션으로 생성·commit한다.
2. 기존 출처 수집 함수를 호출한다. Google의 원자적 요청 예약은 이력과 독립적으로 HTTP 전에 수행한다.
3. 정상 반환 또는 처리 가능한 오류 뒤 최종 상태·종료 시각을 짧은 트랜잭션으로 갱신한다. 이력 트랜잭션을 네트워크 요청 동안 유지하지 않는다.

프로세스가 종료돼 완료 기록을 남기지 못하면 running / finished_at NULL이 남는다. history는 이를 **완료 기록 없음: 진행 중 또는 중단 가능**으로 표시한다. 일정 시간이 지났다는 이유만으로 실패나 성공으로 자동 확정하지 않으며 실제 HTTP 전송 여부·집계도 추정하지 않는다.

이력 시작 저장에 실패하면 해당 출처의 수집을 시작하지 않고 안전한 로컬 오류로 표시한다. 완료 기록 저장에 실패하면 이미 발생한 HTTP·뉴스 저장을 되돌리거나 재요청하지 않고 기록 실패를 CLI에 표시한다. 다른 출처는 계속 처리하며 전체 종료 코드는 1로 한다. 이력 실패와 출처 수집 실패를 구분하고 이전 running 상태는 유지한다. 현재 저장소는 항목을 각각 commit하므로 이력과 뉴스 저장의 전체 원자성을 보장하지 않는다.

### Retention and Query

초기 수동 운영에서는 이력을 자동 삭제하지 않고 로컬 DB에 보관한다. 요청량이 작고 장기 보존 요구가 확인되지 않은 상태에서 자동 삭제로 진단 근거를 잃지 않기 위함이다. 영구 보관을 제품 요구로 확정하는 의미는 아니다. 자동화 전 별도 Issue에서 보관 기간과 명시적 정리 명령을 검토한다.

향후 이력 정리는 이력 테이블만 대상으로 하며 뉴스 항목·HTTP validator·Google 일일 예약을 삭제하지 않는다. 특히 이력 삭제로 당일 요청 한도가 초기화돼서는 안 된다. 초기 구현에는 삭제 CLI를 포함하지 않는다.

history 조회는 started_at 내림차순, 동률이면 run_id 내림차순으로 표시하고 --source 및 양수 --limit을 지원한다. 시간은 timezone을 포함해 표시한다. terminal 상태와 완료 기록이 없는 상태를 구분한다. 기존 수집의 과거 이력을 뉴스나 예약에서 역으로 생성하지 않는다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| 출처별 시작·완료 기록 | 채택. 중단 흔적과 결과를 구분할 수 있으나 두 번의 기록이 필요하다. |
| 완료 결과만 기록 | 구현이 단순하지만 프로세스 중단과 미실행을 구분하기 어렵다. |
| 요청 예약에 결과 필드 추가 | Google 전용 제한 상태와 일반 실행 이력을 혼동하고, 한도 도달 실행을 기록하기 어렵다. |
| 즉시 자동 보존기간 적용 | 운영 규모·진단 요구가 없는 상태에서 삭제 기준을 고정하므로 보류한다. |

## Consequences

후속 구현 Issue에서 SQLite migration·시작/완료 저장 API·coordinator 연결·history CLI·runbook을 추가한다. 상태 전이, 안전한 오류 분류, 중단 상태 조회, 기록 실패 시 요청 미전송과 재요청 금지, 출처별 실패 격리를 테스트한다. 자동화·자동 복구·항목별 관찰 이력은 포함하지 않는다.
