# 0002: Python 3.13 Bootstrap Runtime

- **Status:** Accepted
- **Date:** 2026-09-03
- **Phase:** 2
- **Purpose:** 초기 프로젝트에서 사용할 정확한 Python 마이너 버전을 정의한다.
- **Read when:** 개발 환경을 만들거나 Python 버전 호환성을 검토할 때
- **Related documents:** [기술 스택 기준](../architecture/tech-stack.md), [0001: 뉴스 수집 MVP 기술 스택](0001-news-collection-mvp-tech-stack.md), [2단계 문서](../phases/02-tech-stack-selection.md)

## Context

결정 기록 0001은 CPython 3.13 이상을 승인했지만, 재현 가능한 lockfile과 품질 도구 실행을 위해서는 정확한 Python 마이너 버전이 필요하다. `uv sync`로 CPython 3.13 환경에서 의존성 설치와 품질 도구 실행이 가능한지 확인한다.

## Decision

초기화 작업에서는 CPython 3.13 계열만 허용한다.

- `.python-version`은 `3.13`으로 고정한다.
- `pyproject.toml`의 `requires-python`은 `>=3.13,<3.14`로 설정한다.
- `uv`로 선택·검증한 CPython 3.13 런타임과 lockfile을 사용한다.

이 선택은 기존 승인 범위 안의 세부 구성이며, 사용자가 2026-09-05에 승인했다.

## Options Considered

| 선택지 | 평가 |
|---|---|
| CPython 3.13 | 승인된 최소 버전을 그대로 사용하면서 현재 수집 의존성과 품질 도구를 단일 마이너 버전에서 재현할 수 있다. 채택한 기준이다. |
| CPython 3.14 이상 | 장기적으로 검토할 수 있으나, 현재 승인 기준과 호환성 검증 범위를 불필요하게 넓힌다. |
| `>=3.13`만 지정 | 여러 마이너 버전에서 실행될 수 있어 초기 lockfile·도구 검증의 재현성이 낮다. |

## Consequences

- 장점: 개발·테스트 환경과 lockfile의 Python 기준이 명확해진다.
- 비용: Python 3.14 이상을 사용하려면 호환성 검토와 이 기록의 갱신이 필요하다.
- 후속 작업: 3단계의 실제 수집 구현 전, 새 의존성을 추가할 때 3.13 호환성을 유지한다.
