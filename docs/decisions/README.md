# Decision Records

- **Status:** Active
- **Applies to:** All phases
- **Purpose:** 프로젝트의 중요한 선택과 근거를 다시 확인할 수 있게 기록하는 방법을 정의한다.
- **Read when:** 기술, 제품 또는 운영 방식에 장기적인 영향을 주는 선택을 제안하거나 확정할 때
- **Related documents:** [문서 인덱스](../INDEX.md), [문서 harness](../process/documentation-harness.md), [2단계 문서](../phases/02-tech-stack-selection.md)

## What to Record

다음과 같이 되돌리기 어렵거나 후속 작업에 지속적인 영향을 주는 결정을 기록한다.

- 주 언어, 프레임워크와 데이터 저장 방식
- 시스템 경계와 핵심 아키텍처
- 외부 서비스 또는 공급자 선택
- 데이터 계약과 호환성 정책
- 보안, 개인정보와 운영 비용에 영향을 주는 선택
- 로드맵이나 제품 원칙의 중요한 변경

단순한 파일 이름, 지역적인 리팩터링처럼 쉽게 되돌릴 수 있는 선택은 별도 결정 기록이 필요하지 않다.

## File Naming

결정 문서는 다음 형식을 사용한다.

```text
docs/decisions/0001-short-decision-title.md
```

번호는 기존 기록 다음의 연속된 네 자리 숫자를 사용하고, 제목은 소문자 kebab-case로 작성한다.

## Decision Status

- `Proposed`: 선택지를 검토 중이며 아직 확정되지 않음
- `Accepted`: 사용자와 합의되어 현재 적용되는 결정
- `Rejected`: 검토했지만 채택하지 않음
- `Superseded`: 새 결정으로 대체됨. 새 기록 링크가 필요함

에이전트가 제안한 내용을 사용자 승인 없이 `Accepted`로 기록하지 않는다. 대화에서 사용자가 명시적으로 선택했거나 이미 합의된 프로젝트 결정을 문서화하는 경우에는 그 근거를 남긴다.

## Template

```markdown
# NNNN: Decision Title

- **Status:** Proposed
- **Date:** YYYY-MM-DD
- **Phase:** 관련 단계
- **Related documents:** 상대 경로 링크

## Context

어떤 문제와 제약 때문에 결정이 필요한가?

## Decision

무엇을 선택했는가?

## Options Considered

검토한 선택지와 중요한 장단점은 무엇인가?

## Consequences

얻는 이점, 감수할 비용과 후속 작업은 무엇인가?
```

## Index

| 문서 | 상태 | 답하는 질문 |
|---|---|---|
| [0001: 뉴스 수집 MVP 기술 스택](0001-news-collection-mvp-tech-stack.md) | Accepted | MVP의 기술 기반과 의도적으로 보류한 항목은 무엇인가? |
| [0002: Python 3.13 초기화 런타임](0002-python-3-13-bootstrap-runtime.md) | Proposed | 초기 개발 환경을 어떤 Python 마이너 버전으로 재현하는가? |
