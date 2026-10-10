# Source: Google AI Blog RSS

- **Status:** Accepted
- **Applies to:** Phase 3 approved additional source
- **Purpose:** Google AI Blog RSS의 제한적 운영 승인 조건, 항목 품질과 접근 근거를 기록한다.
- **Read when:** Google AI Blog RSS를 검토하거나 구현 승인 여부를 결정할 때
- **Related documents:** [출처·근거 정책](../policies/source-and-evidence.md), [뉴스 항목 계약](../specs/news-item.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [0005: Google AI Blog RSS 수동 수집 전송](../decisions/0005-google-ai-blog-rss-transport.md), [3단계 문서](../phases/03-news-collection.md)

## Source

| 항목 | 관찰·제안 값 | 근거와 한계 |
|---|---|---|
| `source_id` | `google-ai-blog` | Tech Pilot의 Google RSS 수집기가 사용하는 내부 식별자다. |
| 운영 주체 | Google | [Google AI Blog](https://blog.google/innovation-and-ai/technology/ai/)의 RSS 링크가 [AI RSS endpoint](https://blog.google/innovation-and-ai/technology/ai/rss/)를 가리키는 것을 2026-09-27에 관찰했다. |
| 접근 방식 | RSS | AI RSS endpoint는 익명 HTTP 200과 `application/xml; charset=utf-8`로 응답했다. |
| 접근 endpoint | `https://blog.google/innovation-and-ai/technology/ai/rss/` | 이전 경로 `https://blog.google/technology/ai/rss/`는 이 endpoint로 HTTP 301 redirect됐다. endpoint의 지속성은 보장되지 않는다. |
| 대표 근거 | 각 item의 `link` | 표본 항목의 링크는 `blog.google` 원문 URL이었다. |

AI 카테고리에는 Gemini, 연구, 개발자 도구 등 발표가 함께 포함된다. 이는 개인 AI CTO의 후보 자료로 유용할 수 있지만, 모든 항목이 같은 우선순위를 가진다는 뜻은 아니다.

## Item Quality and Mapping

2026-09-27에 `feedparser`로 응답을 관찰한 결과, XML 파싱 오류 없이 20개 entry를 읽었다. 이는 관찰 시점의 결과이며 고정된 항목 수나 feed 계약이 아니다.

| RSS 관찰 필드 | 뉴스 항목 계약 필드 | 사용 제안 | 한계 |
|---|---|---|---|
| `id` | `external_id` | 비어 있지 않은 entry ID를 출처 내부 ID 후보로 보존 | 표본에서는 원문 URL과 같은 값이었다. 장기 안정성은 구현 전 fixture로 다시 검증한다. |
| `link` | `canonical_url`, `evidence_url` | HTTPS 절대 URL이면 대표 URL과 원문 근거로 사용 | 표본은 `blog.google` 링크였으나 redirect·중계 여부는 항목별로 확인해야 한다. |
| `title` | `title` | 출처가 제공한 제목을 보존 | 빈 제목은 저장하지 않는다. |
| `published` | `published_at`, `published_at_raw` | 파싱 성공 시 시각과 원본 문자열을 함께 보존 | 시각이 없거나 파싱할 수 없으면 현재 시각으로 대체하지 않는다. |
| `updated` | 관찰 전용 필드 | `published`와 다를 때만 향후 변경 시각 후보로 검토 | 현재 뉴스 항목 최소 계약에는 포함하지 않는다. |

표본 entry의 `published`와 `updated`는 모두 `Wed, 23 Sep 2026 18:00:00 +0000`이었다. 한 표본의 일치가 모든 항목의 시각 의미나 갱신 정책을 보장하지는 않는다.

## Access and Policy Evidence

- [robots.txt](https://blog.google/robots.txt)는 2026-09-27에 `search` 경로만 `Disallow`했다. AI RSS endpoint나 AI 카테고리 경로를 대상으로 하는 차단 규칙은 관찰하지 못했다. 이는 자동 접근·보관의 유일한 허가나 약관 동의가 아니다.
- [Google Terms of Service](https://policies.google.com/terms)는 2026-07-30부터 효력이 있는 것으로 표시되며, 서비스의 machine-readable instructions를 위반해 콘텐츠에 자동 수단으로 접근하는 행위를 금지한다. 해당 약관은 RSS의 프로그램 수집 또는 최소 메타데이터 보관을 명시적으로 허용한다고 설명하지 않는다.
- 관찰한 RSS 응답에는 인증 요구, `ETag`, `Last-Modified`, `RateLimit`, `Retry-After` header가 없었다. 프로젝트의 전송·요청 제한은 별도 [결정 기록 0005](../decisions/0005-google-ai-blog-rss-transport.md)를 따른다.
- RSS endpoint가 AI 카테고리 페이지에서 제공되고 같은 `blog.google` 도메인의 원문을 가리키는 사실은 관찰됐다. 그러나 이 사실만으로 프로그램 수집·보관을 포괄적으로 허용하는 별도 근거가 되지는 않는다.

## Practical Access Assessment

**승인 결론:** 사용자가 2026-09-27에 이 기록의 제한적 운영을 승인했다. 이 출처는 [출처·근거 정책의 실무적 RSS 접근 승인 기준](../policies/source-and-evidence.md#practical-rss-access-approval)에 따라 다음 조건을 충족한다.

1. Google AI Blog가 연결한 공개 RSS endpoint이고, 인증·로그인·접근 제어 우회가 필요하지 않다.
2. 관찰한 `robots.txt`에 AI RSS endpoint나 AI 카테고리 경로를 차단하는 규칙이 없다.
3. 관찰한 Google Terms는 machine-readable instructions를 위반하는 자동 접근을 금지하지만, 현재 `robots.txt`를 따르는 최소 메타데이터 수집을 직접 금지하거나 제공자 허가를 요구하는 조항은 확인하지 못했다. 이는 약관 해석의 확정이나 콘텐츠 이용권의 보증은 아니다.
4. `id`, 제목, 원문 URL, 발표 시각과 수집 시각만 뉴스 항목으로 보관하는 매핑을 제안한다. `updated`와 원문 전문·이미지·첨부 파일은 보관하지 않는다.

별도 구현 Issue는 다음 범위에서만 제안할 수 있다.

- AI RSS endpoint에 대한 **하루 1회 이하의 수동 요청**
- 개인용 로컬 SQLite의 내부 조회와 최소 메타데이터 보관
- 자동 재시도·backoff·scheduler 미사용, 뉴스레터·웹사이트·API를 통한 외부 제공 미실시

사용자의 운영 승인은 제3자 약관이나 접근 조건을 대체하지 않으며, endpoint·robots·약관·추가 정책·응답 상태가 바뀌거나 보관·이용 범위를 넓히려면 수집을 중지하고 이 기록을 다시 검토한다. 이 기록을 처음 추가한 PR #32는 출처 승인만 다뤘으며, 당시에는 adapter·수동 수집·scheduler를 구현하거나 실행하지 않았다.

구체적인 HTTP 전송 방식과 KST 기준의 하루 1회 제한은 [0005: Google AI Blog RSS 수동 수집 전송](../decisions/0005-google-ai-blog-rss-transport.md)을 따른다. Issue #41에서 정규화 모듈과 수집 함수를 추가했다. 수집 함수는 HTTP 요청 전에 원자적 예약을 확보하고, 이미 예약된 날에는 `limit_reached`를 반환한다. 잘못된 개별 항목은 제외하고 정상 항목만 저장하며, XML 파싱 실패 때는 항목을 저장하지 않는다. 실제 Google 요청은 아직 실행하지 않았다.

## CLI Integration

Issue #43에서 CLI와 다중 출처 coordinator를 연결했다. `collect` 기본 실행은 Hugging Face와 Google을 순차 처리하며 `--source google-ai-blog`로 Google만 선택할 수 있다. 출처별 결과와 일일 제한의 해석은 [수동 운영 runbook](../runbooks/news-collection.md)을 따른다.

## Follow-up

다음 별도 Issue에서 [OpenAI News RSS](openai-news-rss.md)도 새 실무적 RSS 접근 승인 기준으로 재평가한다. 해당 작업은 OpenAI 약관의 자동·프로그램 방식 추출 제한이 최소 메타데이터 수집을 직접 금지하거나 제공자 허가를 요구하는지 출처 문서에 다시 판단·기록하는 범위이며, adapter·수동 수집·scheduler 구현은 포함하지 않는다.
