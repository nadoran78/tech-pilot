# Source and Evidence Policy

- **Status:** Accepted
- **Applies to:** Phase 3
- **Purpose:** 뉴스 출처를 평가·승인하고 원본 근거와 접근 정책을 일관되게 보존하는 기준을 정의한다.
- **Read when:** 새 출처를 제안·추가하거나 수집 접근 방식과 근거 보존을 검토할 때
- **Related documents:** [수집 아키텍처](../architecture/news-collection.md), [뉴스 항목 계약](../specs/news-item.md), [3단계 문서](../phases/03-news-collection.md)

## Principles

- 기술 발표의 원문이나 공식 공급자의 feed·API를 우선한다.
- 발견 경로와 사실을 뒷받침하는 원문 근거를 분리하지 않고 보존한다.
- 출처가 제공한 사실과 Tech Pilot이 나중에 생성한 요약·분류·추론을 별도 데이터로 다룬다.
- 공개 접근 가능성은 이용 약관, 라이선스, 인증·사용량 제한과 robots 정책을 확인한 뒤 판단한다.
- 수집 편의성보다 출처의 안정성·재현성·정책 준수를 우선한다.

## Access Priority

| 우선순위 | 접근 방식 | 허용 조건 |
|---|---|---|
| 1 | RSS·Atom | 공개 feed URL, 항목 링크·식별자·시각 품질, 접근 정책을 확인한다. |
| 2 | 공식 API | 문서화된 API, 인증 방식, 사용량 제한과 보존 조건을 확인한다. |
| 3 | 승인된 HTML 접근 | RSS·API가 없거나 필요한 사실을 제공하지 않을 때만, 이용 약관·robots·요청 제한·변경 위험을 출처별로 승인한다. |

RSS 2.0은 XML 기반 웹 콘텐츠 신디케이션 형식이며 item 요소를 제공한다. Atom은 feed 안의 entry와 확장 가능한 메타데이터를 정의한다. [RSS 2.0 Specification](https://www.rssboard.org/rss-specification), [RFC 4287](https://www.rfc-editor.org/rfc/rfc4287/)

## Source Approval Record

새 출처는 구현·등록 전에 다음 정보를 제안하고 검토한다.

| 항목 | 확인 내용 |
|---|---|
| 식별 | `source_id`, 운영 주체, 공식성 또는 신뢰 근거 |
| 접근 | feed·API·승인된 HTML URL, 인증 필요 여부, 요청 제한 |
| 항목 품질 | 안정적인 외부 ID, 대표 URL, 제목, 발표 시각의 제공 여부 |
| 정책 | 이용 약관, 라이선스, robots, 재게시·보관 제한 |
| 운영 | timeout·조건부 요청 지원, 실패 시 영향, 구조 변경 위험 |
| 근거 | 대표 원문 URL과 feed·API 문서 URL |

승인 기록에는 실제 비밀 값이나 접근 token을 넣지 않는다. 인증이 필요한 출처는 환경 변수 이름과 필요한 권한만 기록하고 값은 로컬 설정에 둔다.

## Evidence Handling

- 각 뉴스 항목은 `evidence_url`, `source_endpoint`, 출처가 준 제목·시각·외부 ID와 `collected_at`을 보존한다.
- 원문 링크가 중계 페이지인 경우, 확인 가능한 공식 원문 링크를 `evidence_url`로 우선한다.
- 출처에서 얻지 않은 요약, 태그, 중요도, 프로젝트 영향은 원본 필드에 덮어쓰지 않는다.
- 원문 전문과 HTML markup은 출처의 보관·재사용 조건을 확인한 범위에서만 저장하거나 표시한다.

## Automated Access Rules

- robots 규약은 자동 클라이언트의 접근 제어와 오류·cache 처리를 정의한다. HTML 접근 전에는 해당 출처의 robots 규칙을 확인하지만, robots 규칙만으로 이용 약관·저작권·API 사용 조건을 대체하지 않는다. [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html)
- 응답이 `ETag` 또는 `Last-Modified`를 제공하면 출처별로 안전하게 저장하고 다음 요청에 조건부 header로 사용할 수 있다. 조건부 요청 결과가 변경 없음이면 새 뉴스 항목을 만들지 않는다. [RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html)
- 출처별 요청 간격, timeout, 재시도와 user-agent는 실제 출처를 승인할 때 별도로 결정한다.
- 로그인 우회, 접근 제어 우회, robots 규칙 무시, 비공개·유료 콘텐츠의 무단 수집은 허용하지 않는다.

## Deferred Decisions

- 초기 승인 출처 목록과 각 출처의 세부 접근 설정
- 원문 전문·이미지·첨부 파일 보관 정책
- API key가 필요한 출처의 도입 여부
- HTML 접근을 허용할 구체적 출처와 parser 변경 감시 방식
