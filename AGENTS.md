# AGENTS.md

이 문서는 저장소 전체에 적용되는 Codex 작업 진입점이다. 상세 설명을 이 파일에 누적하지 말고, 아래 문서 지도에서 필요한 문서를 찾아 읽는다.

## Mission

이 프로젝트의 장기 목표는 새롭게 등장하는 AI 기술을 지속적으로 수집하고, 사용자의 프로젝트·학습·수익화에 미치는 영향을 분석하는 개인 AI CTO 시스템을 만드는 것이다.

제품 배경과 성공 방향은 [제품 비전](docs/product/vision.md)을 기준으로 한다.

## Current Phase

현재 활성 단계는 **2단계: 기술 스택 선정**이다.

- 현재 범위와 완료 조건: [2단계 문서](docs/phases/02-tech-stack-selection.md)
- 전체 단계와 전환 원칙: [제품 로드맵](docs/product/roadmap.md)
- 전체 문서 목록: [문서 인덱스](docs/INDEX.md)

사용자가 단계 전환을 명시적으로 결정하기 전에는 다음 단계로 넘어가지 않는다. 현재는 기술 선택을 비교·제안하고, 사용자 승인 전에는 기능 코드나 장기 운영 인프라를 작성하지 않는다.

## Required Reading

모든 작업에서 다음 순서로 읽는다.

1. 이 `AGENTS.md`
2. [문서 인덱스](docs/INDEX.md)
3. 인덱스에 표시된 현재 단계 문서
4. 작업과 직접 관련된 문서만 추가로 읽기

작업별 추가 문서는 다음과 같다.

- 제품 목표나 범위 변경: [제품 비전](docs/product/vision.md), [제품 로드맵](docs/product/roadmap.md)
- 문서 추가·분리·이동: [문서 harness](docs/process/documentation-harness.md)
- Issue, 브랜치, PR 또는 병합 작업: [개발 워크플로](docs/process/development-workflow.md)
- 기술 스택 검토: [2단계 문서](docs/phases/02-tech-stack-selection.md), [결정 기록 안내](docs/decisions/README.md)
- 뉴스 수집 설계: [3단계 문서](docs/phases/03-news-collection.md). 단, 3단계가 활성화된 이후에만 상세 설계를 확정한다.

## Working Rules

- 사용자의 요청과 현재 활성 단계의 범위를 함께 지킨다.
- 기존 파일과 사용자 변경사항을 보존하고, 관련 없는 내용을 수정하지 않는다.
- 미결정 사항을 구현 편의상 확정된 결정처럼 취급하지 않는다.
- 사실, 가정, 제안과 확정된 결정을 구분해 기록한다.
- 중요한 기술적 결정은 [결정 기록](docs/decisions/README.md) 절차에 따라 남긴다.
- 비밀 값과 개인정보를 코드, 문서, 로그, fixture에 기록하지 않는다.
- 외부 서비스 게시, 배포 또는 외부 시스템 변경은 사용자의 명시적인 요청 없이 수행하지 않는다.
- 변경 후 작업 유형에 맞는 검증을 수행하고 결과를 보고한다.

## Git Workflow

- `main`은 배포 가능한 릴리스 브랜치이고 `develop`은 일상 개발의 통합 및 기본 브랜치다.
- 일반 작업은 최신 `develop`에서 Issue 번호가 포함된 단기 브랜치를 생성해 진행한다.
- 일반 PR은 `develop`만 대상으로 하며, `main` 대상 PR은 release 또는 hotfix로 제한한다.
- `main`과 `develop`에 직접 push하거나 PR을 자동 병합하지 않는다.
- Issue와 Draft PR의 외부 발행은 사용자의 명시적인 요청이 있을 때만 수행한다.
- 상세 분기, 병합과 예외 규칙은 [개발 워크플로](docs/process/development-workflow.md)를 따른다.

## Handoff Rules

- 작업 완료 응답에는 생성하거나 수정한 파일을 사용자가 이해하기 좋은 검토 순서로 제시한다.
- 파일을 알파벳순으로 나열하지 않고, 맥락과 의존성을 이해할 수 있는 순서로 배열한다.
- 각 파일에는 변경 목적을 한 줄로 설명하고 클릭 가능한 링크를 제공한다.
- 파일이 많으면 진입점, 핵심 설계·구현, 테스트, 보조 문서처럼 그룹화한다.
- 수행한 검증과 검증하지 못한 항목을 함께 알린다.

## Documentation Rules

- 한 문서는 하나의 핵심 질문에 답하도록 유지한다.
- 동일한 내용을 여러 문서에 복사하지 않고 기준 문서를 링크한다.
- 상세 정보를 `AGENTS.md`에 누적하지 않는다.
- 문서를 추가·이동·대체하면 `docs/INDEX.md`와 관련 문서 링크를 함께 갱신한다.
- `docs/` 아래 문서는 상태, 목적, 읽을 시점과 관련 문서를 명시한다.
- 대체된 문서는 새 기준 문서를 가리키고 `Superseded` 상태로 남긴다.
- 자세한 형식과 연결 규칙은 [문서 harness](docs/process/documentation-harness.md)를 따른다.

## Verification

현재는 기술 스택과 실행 명령이 정해지지 않았다. 존재하지 않는 도구나 명령을 추정하지 않는다.

문서 변경 시에는 최소한 다음을 확인한다.

- 모든 상대 링크가 실제 파일을 가리키는가?
- `AGENTS.md`, `README.md`, `docs/INDEX.md`의 현재 단계가 일치하는가?
- 같은 결정이 서로 다른 문서에서 충돌하지 않는가?
- 새 문서가 인덱스나 관련 문서에서 연결되는가?
