# Phase 1: Project Foundation Documents

- **Status:** Accepted
- **Applies to:** Phase 1
- **Purpose:** 프로젝트의 문서 골격과 Codex 작업 경로를 확립한다.
- **Read when:** 현재 단계의 작업 범위나 완료 여부를 판단할 때
- **Related documents:** [문서 인덱스](../INDEX.md), [문서 harness](../process/documentation-harness.md), [제품 로드맵](../product/roadmap.md)

## Goal

사람과 Codex가 프로젝트의 목표, 현재 단계, 확정된 결정과 다음에 읽을 문서를 빠르게 찾을 수 있는 최소 문서 체계를 만든다.

이 단계는 문서의 양을 늘리는 작업이 아니다. 이후 단계에서 필요한 문서를 제때 만들고 일관되게 연결할 수 있는 골격을 만드는 작업이다.

## In Scope

- 프로젝트를 시작한 배경과 장기 비전 정리
- 개발 전 단계를 포함한 제품 로드맵 정리
- `AGENTS.md`를 짧은 Codex 진입점으로 구성
- 사람을 위한 `README.md`와 전체 문서 인덱스 구성
- 문서 분리, 상태, 연결과 갱신 규칙 정의
- 중요한 결정을 남길 위치와 형식 정의
- Issue, 브랜치와 PR의 기본 개발 워크플로 정의
- 반복 가능한 Issue·Draft PR 생성을 위한 저장소 전용 Codex Skill 구성
- 현재 단계와 단계 전환 원칙 명시

## Non-Goals

- 주 개발 언어, 프레임워크 또는 데이터베이스 확정
- 애플리케이션 디렉터리와 빌드 도구 초기화
- 뉴스 출처와 수집 주기 확정
- 뉴스 데이터 스키마와 수집기 아키텍처 설계
- 기능 코드, 테스트 또는 배포 환경 작성

## Deliverables

- [AGENTS.md](../../AGENTS.md)
- [README.md](../../README.md)
- [문서 인덱스](../INDEX.md)
- [제품 비전](../product/vision.md)
- [제품 로드맵](../product/roadmap.md)
- [문서 harness](../process/documentation-harness.md)
- [개발 워크플로](../process/development-workflow.md)
- [결정 기록 안내](../decisions/README.md)
- 1~3단계 범위 문서
- GitHub Issue·PR 템플릿과 저장소 전용 Codex Skill

## Exit Criteria

- 새 Codex 세션이 `AGENTS.md`에서 현재 단계와 다음에 읽을 문서를 찾을 수 있다.
- 모든 현재 문서가 인덱스 또는 연결된 문서에서 도달 가능하다.
- 제품 비전, 로드맵과 현재 단계가 서로 충돌하지 않는다.
- 같은 규칙이나 결정이 여러 문서에서 독립적으로 정의되지 않는다.
- `main`, `develop`과 단기 브랜치의 역할 및 병합 대상이 명확하다.
- Issue와 Draft PR Skill이 사용자 승인 전 외부 상태를 변경하지 않는다.
- 기술 스택과 뉴스 수집의 미결정 사항이 확정된 사실처럼 기록되지 않는다.
- 저장소 내부의 문서 링크가 모두 유효하다.
- 사용자가 문서 골격을 검토하고 2단계 전환 여부를 결정한다.

## Transition

사용자가 2단계 전환을 승인했고, [2단계: 기술 스택 선정](02-tech-stack-selection.md)이 현재 활성 단계다.
