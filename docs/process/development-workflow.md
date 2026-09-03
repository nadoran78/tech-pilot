# Development Workflow

- **Status:** Active
- **Applies to:** All development phases
- **Purpose:** Issue, 브랜치, PR, release와 hotfix의 기본 흐름을 정의한다.
- **Read when:** 작업을 계획하거나 브랜치를 만들고 PR을 발행·검토·병합할 때
- **Related documents:** [문서 인덱스](../INDEX.md), [AGENTS.md](../../AGENTS.md), [1단계 문서](../phases/01-project-foundation.md)

## Branch Roles

| 브랜치 | 역할 | 직접 push | 기본 병합 방식 |
|---|---|---|---|
| `main` | 배포 가능한 운영 버전 | 금지 | release merge commit |
| `develop` | 다음 배포를 위한 통합 및 GitHub 기본 브랜치 | 금지 | 단기 브랜치 squash merge |
| `feature/*` | 기능 개발 | 허용 | `develop`으로 PR |
| `fix/*` | 일반 버그 수정 | 허용 | `develop`으로 PR |
| `docs/*` | 문서 변경 | 허용 | `develop`으로 PR |
| `chore/*` | 설정과 자동화 변경 | 허용 | `develop`으로 PR |
| `hotfix/*` | 운영 긴급 수정 | 허용 | `main`으로 PR 후 `develop`에 역병합 |

일상 개발은 `develop`에서 시작하고 `develop`으로 돌아온다. `main`은 release와 hotfix 외에는 변경하지 않는다.

## GitHub Default Branch

GitHub 기본 브랜치는 `develop`을 사용한다. 일반 PR의 기본 대상을 안전하게 유지하고, `Closes #<issue>`로 연결한 Issue가 기능 완료 시점인 `develop` 병합에서 닫히게 하기 위함이다.

## Issue Policy

다음 작업은 구현 전에 Issue를 만든다.

- 기능, 버그 수정과 동작 변경
- 여러 파일에 영향을 주는 문서 또는 구조 변경
- 기술 결정, 의존성 변경과 운영 자동화
- 별도 완료 조건이나 후속 추적이 필요한 작업

오타나 깨진 링크처럼 범위와 위험이 매우 작은 변경은 Issue를 생략할 수 있다. Issue에는 Goal, Context, Scope, Acceptance Criteria, Non-Goals와 Verification Plan을 적는다.

Issue 발행에는 명시적인 사용자 요청이 필요하다. Codex는 기본적으로 초안과 중복 가능성을 먼저 보여준다.

## Short-Lived Branches

Issue가 발행된 후 최신 `develop`에서 다음 형식으로 브랜치를 만든다.

```text
feature/<issue>-<slug>
fix/<issue>-<slug>
docs/<issue>-<slug>
chore/<issue>-<slug>
hotfix/<issue>-<slug>
```

한 브랜치는 하나의 Issue와 하나의 결과에 집중한다. 관련 없는 변경을 발견하면 현재 PR에 포함하지 않고 별도 Issue로 분리한다.

## Standard Change Flow

1. Issue의 목표, 범위와 완료 조건을 확인한다.
2. 원격 `develop`을 갱신하고 Issue 번호가 포함된 단기 브랜치를 만든다.
3. 범위 안에서 구현하고 관련 검증을 수행한다.
4. base branch와의 전체 diff를 셀프 리뷰한다.
5. 변경을 명확한 커밋으로 기록한다.
6. 사용자 확인 후 `develop` 대상 Draft PR을 생성한다.
7. PR의 변경 파일, 검증 결과와 위험을 다시 검토한다.
8. 준비가 끝나면 사용자가 PR을 Ready로 바꾸고 squash merge한다.
9. 병합된 단기 브랜치를 삭제한다.

`main`과 `develop`에 직접 커밋하거나 push하지 않는다. PR 생성 Skill은 파일을 임의로 stage하거나 커밋하지 않으며, 커밋되지 않은 변경이 있으면 중단한다.

## Pull Request Contract

일반 PR은 다음 조건을 만족해야 한다.

- base가 `develop`이다.
- head가 허용된 단기 브랜치다.
- 하나의 Issue와 연결된다.
- Issue 범위와 실제 diff가 일치한다.
- 실행한 검증과 실행하지 못한 검증을 모두 기록한다.
- 중요한 위험, 후속 작업과 권장 리뷰 순서를 제공한다.
- 사용자 요청 전에는 push하거나 PR을 생성하지 않는다.
- 처음에는 Draft로 생성하고 자동 병합하지 않는다.

## Release Flow

배포 직전에 `develop`에서 `main`으로 Release PR을 만든다.

1. `develop`의 통합 상태와 전체 변경 범위를 확인한다.
2. 배포에 필요한 전체 검증과 릴리스 체크리스트를 수행한다.
3. `develop → main` Draft Release PR을 만든다.
4. 사용자가 검토한 뒤 merge commit으로 병합한다.
5. `main`의 병합 결과에 버전 태그를 만들고 배포한다.

장기 브랜치의 계보를 보존하기 위해 Release PR은 squash merge하지 않는다. release PR 생성, 태그와 배포는 일반 PR Skill의 범위가 아니다. 배포 환경이 정해지면 별도 release Skill과 `docs/runbooks/release.md`를 만든다.

## Hotfix Flow

운영 긴급 수정은 `main`에서 `hotfix/<issue>-<slug>`를 만들고 `main` 대상 PR로 병합한다. 수정이 배포된 뒤 `main`의 변경을 `develop`에 역병합해 다음 release에도 포함한다.

배포 환경이 생기기 전에는 hotfix 자동화나 별도 Skill을 만들지 않는다.

## Responsibilities

- **Codex:** Issue·PR 초안 작성, 사전 조건 검사, diff와 검증 결과 요약, 명시적으로 승인된 외부 발행
- **User:** Issue·PR 내용 확인, 예외 승인, Ready 전환, 최종 병합, release와 배포 결정
- **CI:** 포매팅, 린트, 테스트 등 결정적으로 자동화할 수 있는 검사. 기술 스택 확정 후 추가

## Bootstrap Exception

Git 저장소와 워크플로 자체가 없는 최초 한 번은 현재 골격을 `main`에 직접 bootstrap commit할 수 있다. 이후 `develop`을 기본 브랜치로 만들고 모든 일반 변경에 이 워크플로를 적용한다.

## Branch Protection

GitHub 원격 저장소의 `main`과 `develop`에는 다음 보호 규칙을 적용한다.

- PR을 통해서만 변경할 수 있으며, 관리자 우회도 허용하지 않는다.
- force push와 브랜치 삭제를 허용하지 않는다.
- 개인 프로젝트 흐름에 맞춰 필수 승인 리뷰 수는 `0`으로 유지한다.
- CI가 아직 없으므로 필수 상태 검사와 대화 해결 요구는 설정하지 않는다. CI가 생기면 필수 상태 검사를 연결한다.
