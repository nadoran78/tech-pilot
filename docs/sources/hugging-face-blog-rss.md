# Source: Hugging Face Blog RSS

- **Status:** Accepted
- **Applies to:** Phase 3 initial source candidate
- **Purpose:** Hugging Face Blog RSS를 첫 AI 기술 뉴스 출처로 승인할 수 있는지 판단하는 근거를 기록한다.
- **Read when:** 이 출처를 등록·수집하거나 RSS adapter를 구현·검토할 때
- **Related documents:** [출처·근거 정책](../policies/source-and-evidence.md), [뉴스 항목 계약](../specs/news-item.md), [뉴스 수집 아키텍처](../architecture/news-collection.md), [3단계 문서](../phases/03-news-collection.md)

## Candidate

| 항목 | 제안 값 | 확인 근거 |
|---|---|---|
| `source_id` | `hugging-face-blog` | Tech Pilot 내부에서 사용할 안정적인 출처 이름 제안 |
| 운영 주체 | Hugging Face | [Hugging Face Blog](https://huggingface.co/blog)의 공식 사이트 내 블로그 |
| 접근 방식 | RSS 2.0 | [공개 feed](https://huggingface.co/blog/feed.xml)의 `rss` 문서와 self link |
| 접근 endpoint | `https://huggingface.co/blog/feed.xml` | 2026-09-07에 인증 없이 HTTP 200 응답 확인 |
| 대표 근거 | 각 item의 `link` | feed의 항목 원문 URL |

이 출처는 모델·라이브러리·연구·제품 사용법을 함께 다루므로, 이후 개인 AI CTO의 "새 기술 발표" 기준에 맞는 항목 선별은 별도 작업이 필요하다. 이 기록은 feed 전체가 동일한 중요도를 가진다는 뜻이 아니다.

## Item Quality and Mapping

2026-09-07에 확인한 feed 항목은 다음 필드를 제공했다.

| RSS 필드 | 뉴스 항목 계약 필드 | 사용 제안 | 한계 |
|---|---|---|---|
| `guid` | `external_id` | 비어 있지 않은 값을 출처 내부 ID 후보로 보존 | `isPermaLink` 값이 항목마다 다를 수 있으므로 URL 정규화와 혼동하지 않는다. |
| `link` | `canonical_url`, `evidence_url` | HTTPS 절대 URL이면 대표 URL과 원문 근거로 사용 | 링크가 리디렉션 또는 중계 URL인지 adapter에서 검증한다. |
| `title` | `title` | 출처가 준 제목으로 사용 | 빈 제목은 저장하지 않는다. |
| `pubDate` | `published_at`, `published_at_raw` | 파싱 성공 시 시각과 원문 문자열을 함께 보존 | 파싱 실패 시 현재 시각으로 대체하지 않는다. |

`description`은 확인된 최소 계약에 필요하지 않으며, excerpt 또는 원문 markup 보관 여부는 adapter 구현 전에 출처 정책과 안전성을 다시 검토한다.

## Access and Policy Evidence

- [robots.txt](https://huggingface.co/robots.txt)는 2026-09-07에 `User-agent: *`에 `Allow: /`를 제공했다. 이는 접근 허용 신호일 뿐, 이용 약관·저작권·재게시 권한을 대체하지 않는다.
- feed 응답은 `ETag`를 제공했다. 추후 adapter는 조건부 요청 지원 여부를 실제 구현·테스트에서 결정한다.
- 같은 응답에서 `RateLimit`과 `RateLimit-Policy` header가 관찰됐다. 이는 관찰 시점의 서버 정보일 뿐 지속적인 계약 값으로 고정하지 않는다. timeout·요청 간격·재시도는 이 기록에서 정하지 않는다.
- [Terms of Service](https://huggingface.co/terms-of-service)는 접근 가능하다. 이번 검토에서는 자동 수집이나 콘텐츠 재게시를 포괄적으로 허용한다는 별도 문구를 확정하지 않았다. 실제 수집을 시작하기 전 최신 약관을 다시 확인하고, 제목·링크·필수 메타데이터만 보관하는 최소 범위를 유지한다.
- feed 접근에는 인증이나 비밀 값이 필요하지 않았다. 향후 응답 상태나 정책이 바뀌면 이 기록을 다시 검토한다.

## Approval Assessment

**승인 결론:** 사용자가 2026-09-07에 이 기록을 승인했다. Hugging Face Blog RSS를 첫 수집 출처로 사용하되, 아래 접근 조건을 지킨다.

승인 시 다음 조건을 지킨다.

1. RSS endpoint만 사용하며, feed에 없는 HTML 본문 수집은 별도 승인 없이는 하지 않는다.
2. 원문 전문·이미지·첨부 파일을 저장하거나 재게시하지 않는다.
3. 요청 제한, timeout, conditional HTTP와 user-agent의 구체적인 값은 RSS adapter Issue에서 출처별로 결정한다.
4. feed 구조·robots·약관·응답 상태가 바뀌면 수집을 중지하거나 이 기록을 재검토한다.

## Follow-up

별도 Issue에서 RSS adapter, 항목 정규화, repository 연결과 네트워크 없는 fixture 테스트를 구현한다.
