# 2026-10-10: 첫 다중 출처 수집 품질 검토

- **Status:** Draft
- **Applies to:** Phase 3, Issue #45
- **Purpose:** 실제 다중 출처 수집의 결과·품질·한계를 기록하고 다음 개선의 근거를 제공한다.
- **Read when:** 자동화나 조회 개선을 검토하거나 첫 실제 수집 결과를 리뷰할 때
- **Related documents:** [수동 운영](news-collection.md), [3단계 문서](../phases/03-news-collection.md), [Google 출처](../sources/google-ai-blog-rss.md), [Hugging Face 출처](../sources/hugging-face-blog-rss.md)

## Execution and Access Checks

2026-10-10 14:05 KST에 develop 기준 커밋 `567fb9e`의 CLI로 `data/tech-pilot.sqlite3`를 사용해 `collect`를 한 번 실행했다. 실행 전 DB에는 Hugging Face 867개와 migration 1·2가 있었고 Google 예약 테이블은 없었다. 실행 과정에서 migration 3이 적용됐다. 다른 DB로 전환하거나 Google feed를 재요청하지 않았다.

실행 전 [Hugging Face robots](https://huggingface.co/robots.txt)는 전체 Allow, [Google robots](https://blog.google/robots.txt)는 search 경로의 Disallow만 반환했다. [Hugging Face Terms](https://huggingface.co/terms-of-service)와 [Google Terms](https://policies.google.com/terms)의 관련 접근 조건을 다시 확인했다. 기존 제한적 운영 승인을 변경할 직접적 차단 조건은 확인하지 못했다. 이는 제공자의 포괄적 허가를 새로 확정하는 판단이 아니다.

## Collection Results

| 출처 | 상태 / HTTP | 신규 | 중복 | 검토 필요 | 제외 | 실행 후 총 보관 |
|---|---|---:|---:|---:|---:|---:|
| Hugging Face | completed / 200 | 11 | 865 | 0 | 0 | 878 |
| Google AI Blog | completed / 200 | 20 | 0 | 0 | 0 | 20 |

종료 코드는 0이었다. Google 예약의 KST 날짜는 `2026-10-10`, 예약 시각은 `2026-10-10T05:05:09.218310+00:00`이었다. DB의 뉴스 총수는 898개다. Hugging Face 응답에서 처리된 항목은 876개이며, 기존 보관 전체 867개가 이번 응답에 모두 포함된다는 의미는 아니다.

## Quality Observations

- 신규 Hugging Face 11개와 Google 20개의 제목·URL·발표 시각을 로컬 DB에서 검토했다. 두 출처 전체 보관 항목에서 빈 제목, 발표 시각 누락, HTTPS가 아닌 URL은 각각 0개였다. excerpt와 raw_metadata도 보관되지 않았다.
- 신규 Hugging Face 항목은 모델·음성·에이전트·학습 데이터·GPU 운영 등 기술 주제를 포함했다. 제목만으로 학습 후보를 고르는 데 유용했지만 프로젝트 적용 가능성이나 수익성은 평가하지 않았다.
- Google 20개에는 개발 도구와 제품 발표 외에 인사·행사·문화·일반 제품 활용 소식도 섞여 있었다. 공식 AI 카테고리라는 이유만으로 모두 개발 기술 뉴스로 취급하면 검토 부담이 생긴다. 유용성 비율은 개인 관심 기준이 아직 없으므로 산정하지 않았다.
- 검토한 URL은 각각 `huggingface.co/blog/`와 `blog.google/`에 속했다. Hugging Face에는 조직·커뮤니티 경로가 포함돼 플랫폼 공식 도메인과 게시자의 공식성은 구분해야 한다. 원문을 전수 방문하거나 작성자 신원을 검증하지 않았다.
- Google 최신 저장 항목 하나의 [원문](https://blog.google/innovation-and-ai/technology/ai/playground-experimental-gaming-platform/)을 열어 제목과 게시일 2026-10-07의 일치를 확인했다. 이는 20개 전체 원문의 정확성 보장이 아니다.
- Google 보관 발표 시각 범위는 2026-08-27부터 2026-10-07 UTC였다. 20개라는 유한한 feed 창 때문에 매일 실행해도 모든 과거 발표나 업데이트를 수집한다는 보장은 없다.

## Limits and Next Proposal

이번 실제 실행에서는 실패·304·동시 실행·일일 제한 반환을 재현하지 않았다. 해당 동작은 기존 mock 테스트 근거이며 실제 endpoint에서 검증했다고 기록하지 않는다. Google은 한 번만 요청했다. 기존 DB 중복 처리 결과는 관찰했지만 동일 feed를 즉시 재요청하는 실험은 하지 않았다.

다음 개선 후보는 **list CLI의 출처·수집 시각 필터**다. 현재 최신순 목록만으로는 Google 표본이나 이번 실행의 신규 항목을 찾기 어려워 직접 SQL 조회가 필요했다. 필터는 추가 네트워크 요청 없이 수집 품질을 반복 검토하도록 돕는다. 분류·개인 영향 분석·자동화와 4단계 전환은 이번 결과에 대한 사용자 검토 뒤 별도로 결정한다.

DB와 원본 feed는 Git에 포함하지 않았다. 이 기록은 관찰 결과이며 사용자 품질 승인 전까지 Draft로 유지한다.
