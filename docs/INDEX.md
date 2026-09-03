# Documentation Index

- **Status:** Active
- **Applies to:** All phases
- **Purpose:** 프로젝트 문서의 기준 위치와 읽기 경로를 제공한다.
- **Read when:** 프로젝트 작업을 시작하거나 필요한 문서를 찾을 때
- **Related documents:** [AGENTS.md](../AGENTS.md), [문서 harness](process/documentation-harness.md)

## Current Phase

현재 활성 단계는 **2단계: 기술 스택 선정**이다.

현재 작업에서는 다음 순서로 읽는다.

1. [AGENTS.md](../AGENTS.md)
2. [2단계: 기술 스택 선정](phases/02-tech-stack-selection.md)
3. 작업과 직접 관련된 문서

단계 전환은 완료 조건을 검토한 뒤 사용자가 명시적으로 결정한다.

## Product

| 문서 | 상태 | 답하는 질문 |
|---|---|---|
| [제품 비전](product/vision.md) | Accepted | 왜 이 프로젝트를 만들며 장기적으로 무엇을 해결하는가? |
| [제품 로드맵](product/roadmap.md) | Accepted | 어떤 순서로 프로젝트를 발전시키는가? |

## Process

| 문서 | 상태 | 답하는 질문 |
|---|---|---|
| [문서 harness](process/documentation-harness.md) | Active | 문서를 어떻게 나누고 연결하며 갱신하는가? |
| [개발 워크플로](process/development-workflow.md) | Active | Issue, 브랜치, PR과 릴리스를 어떤 흐름으로 관리하는가? |
| [결정 기록 안내](decisions/README.md) | Active | 중요한 선택과 근거를 어떻게 남기는가? |

## Architecture

| 문서 | 상태 | 답하는 질문 |
|---|---|---|
| [뉴스 수집 MVP 기술 스택](architecture/tech-stack.md) | Accepted | 뉴스 수집 MVP의 최소 기술 기반과 의도적으로 보류한 항목은 무엇인가? |

## Phases

| 단계 문서 | 상태 | 핵심 산출물 |
|---|---|---|
| [1단계: 프로젝트 문서 골격 구성](phases/01-project-foundation.md) | Accepted | 문서 구조와 Codex 작업 경로 |
| [2단계: 기술 스택 선정](phases/02-tech-stack-selection.md) | Active | 기술 스택 결정과 근거 |
| [3단계: AI 기술 뉴스 수집](phases/03-news-collection.md) | Draft | 신뢰 가능한 뉴스 수집 기반 |

4단계 이후의 상세 단계 문서는 해당 단계가 가까워졌을 때 만든다. 전체 방향은 [제품 로드맵](product/roadmap.md)에서 관리한다.

## Documents Created Later

다음 문서는 필요 시점 전에는 만들지 않는다.

- `docs/decisions/NNNN-*.md`: 중요한 결정을 확정할 때
- `docs/architecture/news-collection.md`: 3단계에서 수집 구조를 설계할 때
- `docs/specs/news-item.md`: 3단계에서 뉴스 데이터 계약을 정의할 때
- `docs/policies/source-and-evidence.md`: 3단계에서 출처 정책을 확정할 때
- `docs/runbooks/news-collection.md`: 실제 수집기의 운영 방법이 생겼을 때
- `docs/integrations/obsidian-quartz.md`: 뉴스 품질 검토 후 Obsidian Markdown 작성과 기존 Quartz 블로그 경로 복사를 활성화할 때
- `docs/runbooks/release.md`: 배포 환경이 정해져 release와 hotfix 절차를 운영할 때

새 문서를 만들거나 기존 문서를 대체하면 이 인덱스를 같은 변경에서 갱신한다.
