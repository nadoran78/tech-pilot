# 2026-10-11: 실행 이력 기반 수동 수집 검증

- **Status:** Draft
- **Applies to:** Phase 3, Issue #53
- **Purpose:** 실제 수집 결과와 실행 이력·뉴스 조회의 일관성 및 기존 DB 보존을 기록한다.
- **Read when:** 실행 이력의 실제 운영 근거를 검토하거나 반복 수동 수집 결과를 해석할 때
- **Related documents:** [수동 운영](news-collection.md), [첫 품질 검토](2026-10-10-news-quality-review.md), [실행 이력 결정](../decisions/0006-collection-run-history.md), [3단계](../phases/03-news-collection.md)

## 실행 조건

PR #52가 병합된 develop 커밋 `c223cc3`의 코드로 2026-10-11 17:45 KST에 `collect`를 한 번 실행했다. 사용자가 실제 RSS 요청과 기존 로컬 DB 변경을 포함한 Issue #53 계획을 승인했다. 자동 재시도·추가 수집·304 유도 요청은 하지 않았다.

운영 DB는 기존 `data/tech-pilot.sqlite3`를 그대로 사용했다. 실행 전 migration은 1·2·3, 뉴스는 Hugging Face 878개와 Google 20개, Google 예약은 2026-10-10 한 건이었다. 실행 이력 테이블은 없었다.

SQLite `.backup`으로 `data/history-verification-53-backup.sqlite3`에 변경 전 스냅샷을 만들었다. 백업의 integrity_check는 `ok`, 뉴스 수는 898개였으며 운영 DB와 백업 모두 Git 제외 경로다. 백업을 수집용 DB로 사용하지 않았고 기존 DB를 되돌리거나 예약을 삭제하지 않았다. 이 백업은 검증 근거로 로컬에 남겼으며 정기 백업 정책을 확정한 것은 아니다.

## 접근 조건 재확인

실행 전 현재 [Hugging Face robots](https://huggingface.co/robots.txt)는 전체 Allow, [Google robots](https://blog.google/robots.txt)는 검색 경로 Disallow를 제공했다. 두 승인 RSS 경로의 차단은 관찰하지 못했다.

[Hugging Face Terms](https://huggingface.co/terms-of-service)의 서비스 사용·콘텐츠·지식재산권 조건과 [Google Terms](https://policies.google.com/terms)의 machine-readable instructions 위반 자동 접근 금지 등을 재확인했다. Hugging Face는 자체 제작 자료의 복제·재게시 등에 서면 허가를 요구하며 콘텐츠별 조건도 적용된다. 이번에는 기존 승인 범위인 내부 최소 메타데이터 수집을 변경하지 않았고, 이를 새로 직접 금지하는 조건은 확인하지 못했다. 이는 법률 판단이나 제공자의 포괄적인 수집·보관 허가가 아니다. [출처·근거 정책](../policies/source-and-evidence.md)과 각 출처의 제한적 운영 승인 범위를 유지한다.

## 수집 및 이력 비교

| 출처 | 실행 ID | 상태 / HTTP | 신규 | 중복 | 검토 필요 | 제외 |
|---|---:|---|---:|---:|---:|---:|
| Hugging Face | 1 | unchanged / 304 | 0 | 0 | 0 | 0 |
| Google AI Blog | 2 | completed / 200 | 0 | 20 | 0 | 0 |

collect 종료 코드는 0이었다. 이력 오류는 없었고, `history --limit 20`의 상태·HTTP·네 집계가 수집 요약과 모두 일치했다. 최신 시작 순서인 Google → Hugging Face로 조회됐고 `history --source google-ai-blog --limit 1`에는 Google 한 건만 표시됐다.

- Hugging Face: 시작 `2026-10-11T08:45:36.775048+00:00`, 종료 `2026-10-11T08:45:37.020266+00:00`
- Google: 시작 `2026-10-11T08:45:37.021053+00:00`, 종료 `2026-10-11T08:45:37.475648+00:00`

두 기록 모두 UTC offset과 종료 시각을 가지며 error_code는 NULL이다. 남은 running 기록은 0개다. 뉴스가 새로 저장되지 않은 실행도 이력 조회로 확인할 수 있었다. migration 전 과거 실행을 역으로 생성하지 않아 기존 수집 이력이 새로 나타나지 않았다.

## 뉴스 조회와 기존 데이터 보존

수집 직전 경계 `2026-10-11T08:45:29Z`를 사용해 두 출처 각각 `list --source <source> --collected-since 2026-10-11T08:45:29Z --limit 20`을 실행했다. 모두 빈 목록이며 종료 코드는 0이었다. 신규 0개와 일치하고, Google 중복 20개가 최초 수집 시각 필터에서 제외되는 기존 계약과도 일치한다. 이번 실행은 새 뉴스가 없으므로 신규 항목의 내용·품질은 검토하지 않았다.

백업과 운영 DB를 읽기 전용으로 비교했다.

| 점검 | 관찰 결과 |
|---|---|
| migration | 1·2·3 보존, 4 추가 |
| 기존 뉴스 전체 행 비교 | 누락·변경 0개, 추가 0개; 총 898개 유지 |
| HTTP validator | Hugging Face 행 유지; ETag·Last-Modified 값 동일, updated_at만 이번 304 처리 시각으로 갱신 |
| 기존 Google 예약 전체 행 비교 | 누락·변경 0개 |
| 신규 Google 예약 | 2026-10-11, `2026-10-11T08:45:37.021681+00:00` 한 건 추가 |
| 운영 DB integrity_check | ok |

validator의 updated_at 갱신은 기존 304 처리 구현의 정상 동작이며 모든 validator 행이 바이트 단위로 불변이었다는 뜻은 아니다. 당일 예약이 없었기에 Google은 한 번 요청했다. 추가 실행으로 limit_reached를 유도하지 않았다.

## 한계 및 후속 판단

이번에 실제로 관찰한 것은 정상 migration·304·200 중복 처리·종료 기록·조회 및 기존 데이터 보존이다. 실패 분류, 기록 저장 실패, 진행 중/중단 표시, 동시 실행, 신규 저장과 limit_reached는 실제 운영에서 재현하지 않았다. 해당 계약의 근거는 기존 mock·임시 DB 테스트이며 실제 endpoint 검증과 구분한다.

DB·백업·원본 feed·전체 CLI 출력은 Git이나 PR에 포함하지 않고 집계와 필요한 시각만 기록했다. 코드 수정이 필요한 결함은 이번 검증에서 발견하지 못했다. 자동화·보존 기간·정리 명령은 별도 결정 대상이고, 품질 승인과 4단계 전환은 여전히 사용자 판단을 기다린다. 이 기록은 사용자 검토 전까지 Draft다.
