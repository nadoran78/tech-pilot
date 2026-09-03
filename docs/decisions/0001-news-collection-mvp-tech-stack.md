# 0001: News Collection MVP Technology Stack

- **Status:** Proposed
- **Date:** 2026-09-03
- **Phase:** 2
- **Related documents:** [기술 스택 제안](../architecture/tech-stack.md), [2단계 문서](../phases/02-tech-stack-selection.md), [결정 기록 안내](README.md)

## Context

3단계의 첫 목표는 새 AI 기술 뉴스를 신뢰 가능한 출처에서 반복 수집하고 원본 근거와 함께 보관하는 것이다. 개인 프로젝트의 초기 범위에는 실시간 처리, 다중 사용자, 공개 API, 웹 UI가 없다. 따라서 첫 결과를 빠르게 만들되 후속 요약·분류 단계에 필요한 구조화된 저장을 포기하지 않는 기반이 필요하다.

## Proposed Decision

다음 조합을 MVP 기본안으로 제안한다.

- CPython 3.13 이상과 `uv`
- `argparse` 기반 CLI
- `sqlite3`와 명시적 SQL migration
- `httpx`와 `feedparser`를 사용한 RSS·Atom 우선 수집
- `pytest`, Ruff, mypy를 사용한 최소 품질 검사
- 환경 변수 기반 설정과 로컬 데이터 보관

자동 실행은 수동 CLI가 신뢰 가능한 fixture와 저장 계약을 통과한 뒤 로컬 스케줄러로 검토한다. 이 결정은 사용자의 승인 전까지 `Proposed`이며, 코드·의존성·인프라를 추가하지 않는다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| Python CLI + SQLite | 수집·파싱·데이터 처리에 직접적이고 별도 서버가 없어 MVP 복잡도가 낮다. 제안안이다. |
| TypeScript·Node.js + SQLite | 웹 UI나 기존 Node 환경과의 결합에는 유리할 수 있으나, 현재의 수집 중심 목표에는 별도 이점이 확인되지 않았다. |
| FastAPI + PostgreSQL + 배포 환경 | 다중 사용자·API·동시성이 필요할 때 재검토할 수 있으나 현재 범위에는 과하다. |

## Consequences

- 장점: 작은 CLI 단위로 수집·파싱·중복 방지·보관을 테스트하기 쉽고, 비용과 운영 부담이 낮다.
- 비용: 로컬 실행·SQLite 동시성·출처별 오류 처리를 명시적으로 관리해야 한다.
- 다음 결정: 사용자는 이 제안을 승인·수정·기각할 수 있다. 승인되면 초기화 Issue에서 정확한 Python 버전, 도구 설정과 디렉터리 구조를 구현한다.
