# Documentation Harness

- **Status:** Active
- **Applies to:** All repository documents
- **Purpose:** 사람과 Codex가 필요한 맥락을 빠르게 찾고 일관되게 갱신하는 문서 체계를 정의한다.
- **Read when:** 문서를 추가, 분리, 이동, 대체하거나 문서 간 충돌을 해결할 때
- **Related documents:** [문서 인덱스](../INDEX.md), [AGENTS.md](../../AGENTS.md)

## Core Principles

### Progressive Disclosure

`AGENTS.md`에는 항상 필요한 규칙과 탐색 경로만 둔다. 제품 설명, 단계별 범위, 기술 결정과 운영 방법은 각 기준 문서에서 관리하며 작업에 필요한 문서만 읽는다.

### Single Source of Truth

하나의 결정이나 규칙은 한 문서에서만 정의한다. 다른 문서에서는 짧게 요약한 뒤 기준 문서를 링크한다. 복사된 설명이 서로 달라질 수 있다면 분리하거나 링크로 대체한다.

### Navigable Document Graph

모든 문서는 [문서 인덱스](../INDEX.md) 또는 인덱스에 연결된 문서에서 찾을 수 있어야 한다. 새 문서를 고아 상태로 두지 않는다.

### Explicit State

초안, 현재 기준, 합의된 내용과 폐기된 내용을 구분한다. 아직 결정하지 않은 내용을 확정된 사실처럼 쓰지 않는다.

## Document Header

`docs/` 아래의 문서는 특별한 이유가 없다면 다음 정보를 제목 바로 아래에 둔다.

```markdown
- **Status:** Draft | Active | Accepted | Superseded
- **Applies to:** 적용 단계 또는 범위
- **Purpose:** 이 문서가 답하는 핵심 질문
- **Read when:** 이 문서를 읽어야 하는 상황
- **Related documents:** 상대 경로 링크
```

상태의 의미는 다음과 같다.

- `Draft`: 검토 중이며 아직 기준으로 확정되지 않음
- `Active`: 현재 작업이나 운영에서 사용하는 기준
- `Accepted`: 합의되어 유지되는 제품 또는 기술 결정
- `Superseded`: 다른 문서로 대체됨. 대체 문서 링크가 필요함

## Document Boundaries

- 한 문서는 하나의 핵심 질문 또는 비슷한 수명 주기를 가진 내용만 다룬다.
- 서로 다른 독자, 변경 주기 또는 승인 절차가 필요하면 문서를 분리한다.
- 단순히 파일 길이를 줄이기 위해 맥락을 지나치게 잘게 쪼개지 않는다.
- 상세 내용이 `AGENTS.md`에 쌓이면 적절한 기준 문서로 이동하고 링크만 남긴다.
- 아직 사용할 시점이 오지 않은 상세 문서는 만들지 않고 인덱스에 예상 산출물로 기록한다.

## Placement

- `docs/product/`: 제품 비전, 목표와 로드맵
- `docs/process/`: 작업과 문서 운영 방식
- `docs/phases/`: 단계별 목표, 범위와 완료 조건
- `docs/decisions/`: 중요한 기술·제품 결정과 근거
- `docs/architecture/`: 확정된 시스템 구조. 필요해질 때 생성
- `docs/specs/`: 데이터와 인터페이스 계약. 필요해질 때 생성
- `docs/integrations/`: 외부 애플리케이션이나 저장소와의 연동 계약. 연동 작업이 활성화될 때 생성
- `docs/policies/`: 출처, 보안 등 반복 적용 정책. 필요해질 때 생성
- `docs/runbooks/`: 실제 운영 절차. 운영 대상이 생긴 뒤 생성

파일 이름은 소문자 kebab-case를 사용한다. 단계 문서는 정렬 가능한 두 자리 번호를 앞에 붙인다.

## Linking and Updates

- 저장소 내부 문서는 상대 경로로 연결한다.
- 문서를 추가하거나 이동하면 `docs/INDEX.md`와 관련 문서를 같은 변경에서 갱신한다.
- 현재 단계가 바뀌면 최소한 `AGENTS.md`, `README.md`, `docs/INDEX.md`, `docs/product/roadmap.md`를 함께 확인한다.
- 문서를 대체할 때 기존 문서를 바로 삭제하지 말고 `Superseded`로 표시한 뒤 새 기준 문서를 연결한다.
- 충돌을 발견하면 현재 활성 문서와 승인된 결정 기록을 우선 확인하고, 임의로 한쪽을 선택하지 않는다.

## Reading Strategy for Codex

1. `AGENTS.md`에서 현재 단계와 공통 규칙을 확인한다.
2. `docs/INDEX.md`에서 현재 단계 문서와 작업별 기준 문서를 찾는다.
3. 현재 단계 문서를 읽고 범위와 완료 조건을 확인한다.
4. 구현이나 결정에 필요한 문서만 추가로 읽는다.
5. 새 결정이나 변경으로 문서 지도가 달라졌다면 링크를 함께 갱신한다.

## Phase Document Shape

단계 문서는 가능하면 다음 내용을 포함한다.

- 목표
- 현재 범위
- 하지 않는 일
- 필요한 입력과 선행 결정
- 산출물
- 완료 조건
- 다음 단계로 넘어가는 방법

상세 데이터 계약이나 구현 방법은 단계 문서에 누적하지 않고 별도의 명세, 아키텍처 또는 결정 문서로 분리한다.
