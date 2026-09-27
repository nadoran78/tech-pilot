# Source Candidate: OpenAI News RSS

- **Status:** Proposed
- **Applies to:** Phase 3 second source candidate
- **Purpose:** OpenAI News RSS를 수집 후보로 승인·보류·기각할 때 필요한 접근 정책, 항목 품질과 운영 근거를 기록한다.
- **Read when:** OpenAI News RSS를 검토하거나 구현 승인 여부를 결정할 때
- **Related documents:** [출처·근거 정책](../policies/source-and-evidence.md), [뉴스 항목 계약](../specs/news-item.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [3단계 문서](../phases/03-news-collection.md)

## Candidate

| 항목 | 관찰·제안 값 | 근거와 한계 |
|---|---|---|
| `source_id` | `openai-news` | Tech Pilot 내부에서 사용할 제안 식별자다. 아직 구현에 등록하지 않는다. |
| 운영 주체 | OpenAI | OpenAI 사이트 전역 footer의 RSS 링크가 [endpoint](https://openai.com/news/rss.xml)를 가리키며, 같은 `openai.com` 도메인의 feed 제목이 `OpenAI News`로 관찰됐다. |
| 접근 방식 | RSS | [RSS endpoint](https://openai.com/news/rss.xml)는 2026-09-27에 익명 HTTP 200과 `text/xml; charset=utf-8`로 응답했다. |
| 접근 endpoint | `https://openai.com/news/rss.xml` | 관찰 시 redirect 없이 최종 URL이 같았다. endpoint의 지속성은 보장되지 않는다. |
| 대표 근거 | 각 item의 `link` | 표본 항목의 링크는 `openai.com` 원문 URL이었다. |

공식 News 목록은 제품·연구·안전 등 여러 범주의 발표를 함께 제공한다. 이는 개인 AI CTO의 후보 자료로는 유용할 수 있지만, 모든 항목이 같은 우선순위를 가진다는 뜻은 아니다.

## Item Quality and Mapping

2026-09-27에 `feedparser`로 응답을 관찰한 결과, XML 파싱 오류 없이 1,230개 entry를 읽었다. 이는 관찰 시점의 결과이며 고정된 항목 수나 feed 계약이 아니다.

| RSS 관찰 필드 | 뉴스 항목 계약 필드 | 사용 제안 | 한계 |
|---|---|---|---|
| `id` | `external_id` | 비어 있지 않은 entry ID를 출처 내부 ID 후보로 보존 | 표본에서는 원문 URL과 같은 값이었다. 장기 안정성은 구현 전 fixture로 다시 검증한다. |
| `link` | `canonical_url`, `evidence_url` | HTTPS 절대 URL이면 대표 URL과 원문 근거로 사용 | 표본은 `openai.com` 링크였으나 redirect·중계 여부는 항목별로 확인해야 한다. |
| `title` | `title` | 출처가 제공한 제목을 보존 | 빈 제목은 저장하지 않는다. |
| `published` | `published_at`, `published_at_raw` | 파싱 성공 시 시각과 원본 문자열을 함께 보존 | 시각이 없거나 파싱할 수 없으면 현재 시각으로 대체하지 않는다. |

표본 entry에서는 category를 관찰하지 못했다. 카테고리는 현재 뉴스 항목 최소 계약에 필요하지 않으므로, 향후 수집 구현에서 임의로 추론하거나 저장하지 않는다.

## Access and Policy Evidence

- [robots.txt](https://openai.com/robots.txt)는 2026-09-27에 `User-agent: *`에 대해 `Allow: /`를 제공하고 `/microsoft-for-startups/`만 제외했다. 이는 자동 접근의 유일한 허가나 약관 동의가 아니다.
- [Terms of Use](https://openai.com/policies/row-terms-of-use/)는 2026-01-01부터 효력이 있는 것으로 표시되며, 웹사이트를 포함한 Services에서 데이터를 자동·프로그램 방식으로 추출하는 행위를 금지한다. 공개 RSS 또는 최소 메타데이터 보관에 대한 예외·허가 문구는 확인하지 못했다.
- 관찰한 RSS 응답에는 인증 요구, `ETag`, `Last-Modified`, `RateLimit` header가 없었다. 따라서 조건부 요청·요청 간격·timeout·재시도 정책은 이 후보에 대해 아직 제안하지 않는다.
- RSS endpoint가 공개돼 있고 같은 도메인의 News를 가리킨다는 사실은 관찰됐다. 그러나 RSS 제공이 자동 수집·보관을 포괄적으로 허가한다는 별도 근거는 확인하지 못했다.
- 사용자가 2026-09-26에 제공한 OpenAI 고객센터 응답은 공개 문서만으로 이 endpoint의 프로그램 수집·최소 메타데이터 보관을 명시적으로 허용하거나 금지한다고 단정할 근거가 없다고 안내했다. 이 개별 응답은 약관의 예외나 제공자의 명시적 허가가 아니다.

## Practical Access Assessment

**운영 판단: 제한적 운영 승인 불가.** 이 후보는 [출처·근거 정책의 실무적 RSS 접근 승인 기준](../policies/source-and-evidence.md#practical-rss-access-approval) 중 공식 endpoint, 인증 불필요, robots 비차단과 최소 메타데이터 매핑 조건은 충족한다. 그러나 OpenAI Terms가 웹사이트를 포함한 Services에서 데이터를 자동·프로그램 방식으로 추출하는 행위를 직접 금지하므로, 약관·추가 정책에서 최소 수집을 직접 금지하거나 제공자 허가를 요구하면 승인하지 않는 정책 조건을 충족하지 못한다.

RSS 예외가 약관에 명시되지 않았고, 고객센터 응답도 그 적용 범위에 관한 허가를 제공하지 않았다. 이는 약관의 법적 해석을 확정하는 결론이 아니라, 현재 공개 근거에 따른 보수적인 운영 판단이다. 따라서 `Proposed` 상태를 유지하고 adapter, 수동 수집, scheduler를 구현하거나 실행하지 않는다. 사용자의 승인이나 위험 인지만으로는 이 조건을 대체할 수 없다.

## Follow-up

OpenAI가 공개 RSS의 프로그램 수집과 최소 메타데이터 보관을 명시적으로 허용하는 최신 정책·문서 또는 권한 있는 서면 답변을 제공하면 이 기록을 다시 검토한다. 사용자가 수집하지 않고 후보를 유지하거나 기각하기로 결정하면, 구현 Issue를 만들지 않고 이 후보 문서의 상태와 근거만 갱신한다.
