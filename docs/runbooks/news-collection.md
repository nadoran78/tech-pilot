# 뉴스 수집 수동 운영

- **Status:** Active
- **Applies to:** 3단계의 승인된 Hugging Face 및 Google AI Blog RSS 수동 수집
- **Purpose:** 로컬에서 RSS를 한 번 수집하고 저장된 항목과 수집 결과를 안전하게 점검하는 절차를 제공한다.
- **Read when:** 실제 RSS 수집을 실행하거나 출처별 결과와 일일 요청 제한을 해석할 때
- **Related documents:** [3단계 문서](../phases/03-news-collection.md), [Hugging Face Blog RSS 출처](../sources/hugging-face-blog-rss.md), [0004: Hugging Face RSS 수집 전송](../decisions/0004-hugging-face-rss-transport.md), [뉴스 항목 계약](../specs/news-item.md)

## Scope and Preconditions

이 runbook은 승인된 `hugging-face-blog`와 [Google AI Blog RSS](../sources/google-ai-blog-rss.md)의 순차 수동 수집을 다룬다. 스케줄러, 자동 재시도와 원문 전문 수집은 범위에 포함하지 않는다.

수집 전에 다음을 확인한다.

1. 선택한 출처의 endpoint, 접근 조건과 보관 범위를 각 출처 기록에서 확인한다.
2. 최신 `robots.txt`, Terms of Service와 출처별 추가 정책을 확인해, 이전 기록 이후 접근 조건이 바뀌지 않았는지 점검한다. 출처 문서의 운영 승인 범위와 달리 인증·접근 제어가 필요해졌거나, 최소 수집을 직접 금지하거나 제공자 허가를 요구하는 조건을 발견하면 수집하지 않고 출처 기록을 재검토한다. robots 규칙은 약관이나 저작권 조건을 대체하지 않는다.
3. 로컬 환경에서 의존성을 준비한다.

```bash
uv sync
```

실제 수집은 네트워크 요청과 로컬 DB 변경을 수행한다. 실행 전 사용자가 이를 의도했는지 확인하고, 인증 정보나 비밀 값은 명령행·문서·로그에 넣지 않는다.

## Collect Once

기본 DB 경로는 Git에서 제외되는 `data/tech-pilot.sqlite3`다.

```bash
uv run tech-pilot collect
```

다른 로컬 DB를 사용해 실험하려면 경로를 명시한다.

```bash
uv run tech-pilot collect --database /path/to/news.sqlite3
```

기본 실행은 Hugging Face와 Google을 순서대로 처리한다. 한 출처의 실패나 제한 도달 뒤에도 나머지 출처는 계속 실행한다. 하나만 수집하려면 다음 옵션을 사용한다.

```bash
uv run tech-pilot collect --source hugging-face-blog
uv run tech-pilot collect --source google-ai-blog
```

각 출처에 GET 요청을 최대 한 번 보낸다. Hugging Face의 조건부 요청은 [결정 기록 0004](../decisions/0004-hugging-face-rss-transport.md)의 현재 구현을 유지하며, 이 결정은 여전히 `Proposed`다. Google은 승인된 [결정 기록 0005](../decisions/0005-google-ai-blog-rss-transport.md)에 따라 KST 달력 날짜별 한 번만 요청하고, 실패한 시도도 포함한다. 같은 날짜에 예약이 있으면 요청하지 않는다. 예약은 지정한 SQLite DB에 저장되므로 운영에는 같은 DB를 지속해서 사용한다. 별도 DB는 전역 요청 한도를 공유하지 않으며, DB 변경·삭제로 한도를 우회하지 않는다.

## Inspect Stored Items

수집 후 저장 항목의 제목, 출처, 원문 URL, 발표 시각과 수집 시각을 확인한다.

```bash
uv run tech-pilot list --limit 20
```

다른 DB를 사용했다면 같은 경로를 지정한다.

```bash
uv run tech-pilot list --database /path/to/news.sqlite3 --limit 20
```

목록은 발표 시각이 있는 항목을 실제 시점 기준 내림차순으로 먼저 표시한다. 발표 시각이 같으면 수집 시각과 저장 ID 내림차순을 사용하며, 발표 시각이 없는 항목은 마지막에 표시한다. `list`는 출처·최초 수집 시각 필터를 제공하며 제목 검색은 제공하지 않는다.

## Interpret the Result

품질 검토용 조회는 다음 필터를 함께 사용할 수 있다. 필터 적용 뒤 기존 최신순 정렬과 `--limit`을 유지한다.

```bash
uv run tech-pilot list --source google-ai-blog --limit 20
uv run tech-pilot list --collected-since 2026-10-10T14:00:00+09:00
uv run tech-pilot list --source google-ai-blog --collected-since 2026-10-10T05:00:00Z
```

`--collected-since`는 timezone이 포함된 ISO 8601 시각을 받아 같은 실제 시점으로 비교하고 경계 시각을 포함한다. 최초 저장 시각을 기준으로 하므로 재관찰한 중복 항목은 이번 수집 결과 목록에 포함되지 않을 수 있다. 실행별 관찰 이력 기능은 아니다. 필터를 생략하면 기존 조회 동작을 유지한다.

| 상태 | 종료 코드 | 의미 | 다음 행동 |
|---|---:|---|---|
| `completed` | 0 | HTTP 2xx 응답을 신뢰할 수 있게 파싱해 신규·중복·제외 수를 집계했다. | `list`로 원문 URL, 제목, 출처와 시각을 점검한다. |
| `unchanged` | 0 | HTTP 304로 이전 validator 이후 feed 변경이 없었다. | 새 항목이 없다는 정상 결과다. 필요할 때 다음 수동 실행을 한다. |
| `limit_reached` | 0 | Google의 같은 KST 날짜 요청 예약이 이미 있어 HTTP 요청을 보내지 않았다. | 다음 KST 날짜까지 기다린다. |
| `failed` | 1 | HTTP 요청·상태 또는 RSS 파싱에 실패했다. | 오류 요약과 출처의 현재 endpoint·정책을 점검한 뒤, 필요할 때만 다시 한 번 실행한다. |

출처별로 요약 한 줄을 출력한다. 전체 종료 코드는 하나라도 `failed`이거나 이력 기록 오류가 있으면 `1`, 그 외에는 `0`이다. 저장소 등 로컬 처리 오류도 안전한 실패 요약으로 표시하고 다음 출처를 실행한다. `failed` 결과에서는 손상된 RSS 응답의 HTTP validator를 저장하지 않는다. Google은 실패 뒤에도 당일 예약을 유지한다. 자동 재시도·backoff는 하지 않는다.

## Inspect Collection History

출처별 실행 이력은 [결정 기록 0006](../decisions/0006-collection-run-history.md)에 따라 같은 DB에 보관한다. 뉴스 목록과 달리 신규 항목이 없는 실행도 확인할 수 있다.

```bash
uv run tech-pilot history --limit 20
uv run tech-pilot history --source google-ai-blog --limit 10
uv run tech-pilot history --database /path/to/news.sqlite3
```

시작 시각과 실행 ID 내림차순으로 조회한다. 시각은 UTC offset을 포함한다. 실패한 실행의 집계 `None`은 처리량 미확정이며 0개라는 뜻이 아니다. `완료 기록 없음: 진행 중 또는 중단 가능`은 종료 기록이 없다는 뜻으로, 요청 여부나 성공·실패를 확정하지 않는다.

- `history_start_failed`: 시작 기록 실패로 해당 출처의 요청을 보내지 않았다. DB 접근·여유 공간을 점검한다.
- `history_finish_failed`: 수집 결과와 별개로 종료 기록에 실패했다. 수집 요약과 뉴스 목록을 함께 점검하며, 기록을 완성하려고 재요청하지 않는다.

두 경우 모두 다른 출처 처리는 계속한다. Google 당일 요청 예약과 이력은 독립적이므로 기록 실패를 이유로 DB 변경·삭제를 통해 한도를 우회하지 않는다. 기존 실행의 이력은 역으로 생성하지 않으며 자동 삭제·복구·정리 명령은 제공하지 않는다.

## Review the First Real Collection

2026-10-10 실제 실행의 집계와 관찰 한계는 [첫 품질 검토 기록](2026-10-10-news-quality-review.md)에 있다. 이후 실행도 같은 기준으로 기록한다.

첫 실제 수집에서는 다음을 확인하고 사용자와 결과를 검토한다.

1. 제목·원문 URL이 실제 AI 기술 발표를 판단하는 데 충분한지 확인한다.
2. 발표 시각이 있는 항목과 없는 항목의 비율, feed의 항목 수와 불필요한 항목 비율을 확인한다.
3. 원문 URL이 각 출처의 공식 원문을 가리키는지 표본으로 확인한다.
4. Hugging Face 단독 실행에서 `unchanged`가 관찰되면 조건부 요청 동작을 기록한다. Google은 같은 날 재실행하면 `limit_reached`가 정상 결과다.
5. 로컬 DB와 수집 출력에는 외부 콘텐츠가 포함될 수 있으므로 Git에 추가하거나 PR에 붙이지 않는다.

이 검토 결과를 바탕으로 사용자만이 4단계 전환, 두 번째 출처 조사 또는 결정 기록 0004의 승인 여부를 결정한다.
