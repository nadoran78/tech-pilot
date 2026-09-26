# 뉴스 수집 수동 운영

- **Status:** Active
- **Applies to:** 3단계의 승인된 Hugging Face Blog RSS 수동 수집
- **Purpose:** 로컬에서 RSS를 한 번 수집하고 저장된 항목과 수집 결과를 안전하게 점검하는 절차를 제공한다.
- **Read when:** 실제 RSS 수집을 실행하거나 `completed`, `unchanged`, `failed` 결과를 해석할 때
- **Related documents:** [3단계 문서](../phases/03-news-collection.md), [Hugging Face Blog RSS 출처](../sources/hugging-face-blog-rss.md), [0004: Hugging Face RSS 수집 전송](../decisions/0004-hugging-face-rss-transport.md), [뉴스 항목 계약](../specs/news-item.md)

## Scope and Preconditions

이 runbook은 현재 승인된 `hugging-face-blog` 출처만 다룬다. 스케줄러, 자동 재시도, 다중 출처와 원문 전문 수집은 범위에 포함하지 않는다.

수집 전에 다음을 확인한다.

1. 현재 출처 기록의 endpoint, 접근 조건과 보관 범위를 [Hugging Face Blog RSS 출처](../sources/hugging-face-blog-rss.md)에서 확인한다.
2. 최신 `robots.txt`와 Terms of Service 페이지에 접근해, 이전 기록 이후 접근 정책이나 응답 상태가 바뀌지 않았는지 확인한다. robots 규칙은 약관이나 저작권 조건을 대체하지 않는다.
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

한 실행은 endpoint에 GET 요청을 한 번만 보낸다. timeout, user-agent, 조건부 요청과 재시도 정책의 현재 제안은 [결정 기록 0004](../decisions/0004-hugging-face-rss-transport.md)를 기준으로 한다. 이 결정은 아직 `Proposed` 상태이므로, 운영 정책을 확정하거나 자동화하지 않는다.

## Inspect Stored Items

수집 후 저장 항목의 제목, 출처, 원문 URL, 발표 시각과 수집 시각을 확인한다.

```bash
uv run tech-pilot list --limit 20
```

다른 DB를 사용했다면 같은 경로를 지정한다.

```bash
uv run tech-pilot list --database /path/to/news.sqlite3 --limit 20
```

목록은 발표 시각이 있는 항목을 실제 시점 기준 내림차순으로 먼저 표시한다. 발표 시각이 같으면 수집 시각과 저장 ID 내림차순을 사용하며, 발표 시각이 없는 항목은 마지막에 표시한다. 현재 `list`는 품질 확인용 최소 인터페이스이며, 검색·필터링은 제공하지 않는다.

## Interpret the Result

| 상태 | 종료 코드 | 의미 | 다음 행동 |
|---|---:|---|---|
| `completed` | 0 | HTTP 2xx 응답을 신뢰할 수 있게 파싱해 신규·중복·제외 수를 집계했다. | `list`로 원문 URL, 제목, 출처와 시각을 점검한다. |
| `unchanged` | 0 | HTTP 304로 이전 validator 이후 feed 변경이 없었다. | 새 항목이 없다는 정상 결과다. 필요할 때 다음 수동 실행을 한다. |
| `failed` | 1 | HTTP 요청·상태 또는 RSS 파싱에 실패했다. | 오류 요약과 출처의 현재 endpoint·정책을 점검한 뒤, 필요할 때만 다시 한 번 실행한다. |

`failed` 결과에서는 손상된 RSS 응답의 HTTP validator를 저장하지 않는다. 재시도·backoff는 아직 구현하지 않았으므로, 짧은 간격의 반복 요청은 하지 않는다.

## Review the First Real Collection

첫 실제 수집에서는 다음을 확인하고 사용자와 결과를 검토한다.

1. 제목·원문 URL이 실제 AI 기술 발표를 판단하는 데 충분한지 확인한다.
2. 발표 시각이 있는 항목과 없는 항목의 비율, feed의 항목 수와 불필요한 항목 비율을 확인한다.
3. 원문 URL이 Hugging Face의 공식 원문을 가리키는지 표본으로 확인한다.
4. `completed` 뒤 즉시 한 번 더 실행했을 때 `unchanged`가 나오면 조건부 요청 동작을 기록한다. endpoint가 새 응답을 내면 이를 실패로 해석하지 않는다.
5. 로컬 DB와 수집 출력에는 외부 콘텐츠가 포함될 수 있으므로 Git에 추가하거나 PR에 붙이지 않는다.

이 검토 결과를 바탕으로 사용자만이 4단계 전환, 두 번째 출처 조사 또는 결정 기록 0004의 승인 여부를 결정한다.
