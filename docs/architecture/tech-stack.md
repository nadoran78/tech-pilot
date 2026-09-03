# News Collection MVP Tech Stack

- **Status:** Accepted
- **Applies to:** Phase 2
- **Purpose:** 3단계 뉴스 수집 MVP를 위한 최소 기술 기반, 근거와 보류 결정을 한 곳에서 관리한다.
- **Read when:** 기술 스택을 검토·승인하거나 3단계 구현을 시작하기 전
- **Related documents:** [2단계 문서](../phases/02-tech-stack-selection.md), [기술 스택 결정](../decisions/0001-news-collection-mvp-tech-stack.md), [Python 3.13 초기화 결정](../decisions/0002-python-3-13-bootstrap-runtime.md), [3단계 문서](../phases/03-news-collection.md)

## Decision State

사용자가 2026-09-03에 이 기준을 승인했다. 여기의 선택과 [기술 스택 결정](../decisions/0001-news-collection-mvp-tech-stack.md)은 `Accepted` 상태다. 초기화 작업의 Python 3.13 세부 선택은 [결정 기록 0002](../decisions/0002-python-3-13-bootstrap-runtime.md)에서 검토 중이며, 자동 실행 환경은 의도적으로 이후 수집 설계 Issue에서 결정한다.

## Working Assumptions

- 한 명이 유지하는 개인 프로젝트이며, 첫 목표는 신뢰 가능한 AI 기술 뉴스의 반복 수집·보관이다.
- 초기 수집량은 작고, 실시간 처리·다중 사용자·공개 API는 필요하지 않다.
- 출처는 RSS·Atom과 공식 API를 우선하고, HTML 접근은 출처별 정책을 검토한 뒤 제한적으로 추가한다.
- 수집 데이터와 비밀 값은 Git에 기록하지 않으며, 첫 자동 실행 환경은 로컬 개발 환경을 기준으로 한다.
- 이 가정 중 하나라도 달라지면 영향과 함께 새 결정 기록에서 기준을 다시 평가한다.

## Accepted Baseline

| 결정 영역 | 선택 | 이유 | 지금 하지 않는 것 |
|---|---|---|---|
| 언어·런타임 | CPython 3.13 이상 | 수집·파싱·분석 생태계가 풍부하고, 표준 라이브러리의 `sqlite3`, `argparse`, `logging`으로 초기 의존성을 낮출 수 있다. | 초기화 PR에서는 3.13 계열을 제안하며, 최종 상태는 [결정 기록 0002](../decisions/0002-python-3-13-bootstrap-runtime.md)에서 관리한다. |
| 프로젝트·의존성 관리 | `uv`와 `pyproject.toml`·lockfile | Python 버전, 환경, 의존성, lockfile을 한 도구로 관리할 수 있다. | 패키지 배포나 workspace 구성 |
| 첫 실행 형태 | `argparse` 기반 CLI | 수집을 재현·테스트하기 쉽고 API나 웹 UI 없이도 수동 실행과 스케줄러 연결이 가능하다. | HTTP API, 웹 애플리케이션, 대시보드 |
| 저장 방식 | 표준 라이브러리 `sqlite3`와 명시적 SQL migration | 별도 서버 없이 디스크 기반 저장을 시작할 수 있고, 이후 더 큰 DB로 옮길 경로가 있다. | ORM, 외부 DB, 벡터 DB |
| HTTP·피드 수집 | `httpx` + `feedparser` | HTTPX는 동기·비동기 API와 명시적 timeout을 제공하며, feedparser는 RSS·Atom과 날짜·인코딩·피드 오류 처리 기능을 제공한다. | 동시성 최적화, 범용 HTML 크롤러 |
| 출처 우선순위 | RSS·Atom → 공식 API → 승인된 HTML 접근 | 출처의 안정성·재현성·정책 준수에 유리하다. | robots 정책을 무시하는 수집 |
| 품질 도구 | `pytest`, Ruff, mypy | 테스트, lint·format, 점진적 정적 타입 검사를 각자의 역할로 분리해 최소 피드백 루프를 만든다. | CI 필수 검사와 과도한 strict 설정 |
| 설정·비밀 값 | 환경 변수와 `.env` 로컬 오버라이드 | 비밀 값을 저장소에서 분리하고 표준 `os.environ`으로 접근할 수 있다. | 실제 API 키, 비밀 관리 SaaS |
| 자동 실행 | 수동 CLI를 먼저 검증한 뒤 로컬 스케줄러를 제안 | 데이터 저장 위치와 실패 복구 요구가 확인되기 전에는 클라우드 스케줄러를 고정하지 않는다. | GitHub Actions 기반 수집·외부 호스팅 |

## Alternatives Considered

| 대안 | 보류·기각 이유 |
|---|---|
| TypeScript·Node.js 중심 수집기 | 웹 UI가 필요해질 수 있으나, 현재 목표는 수집·정규화·저장이며 Python의 데이터 처리 생태계와 단순한 표준 SQLite 경로가 더 직접적이다. |
| 처음부터 FastAPI·웹 UI | 개인용 수집 MVP의 첫 유용한 결과를 늦추고, 인증·배포·운영 결정을 앞당긴다. |
| PostgreSQL 또는 관리형 DB | 초기 데이터량과 단일 실행 환경에는 별도 서버·비용·운영 부담이 크다. |
| 범용 HTML 크롤링을 첫 수집 방식으로 채택 | 출처별 구조 변화, 접근 정책, 재현성 위험이 RSS·공식 API보다 크다. |
| GitHub Actions를 즉시 스케줄러로 사용 | 공개 저장소의 데이터·비밀 값·SQLite 지속성 요구를 먼저 확인해야 한다. |

## Initial Project Shape

다음 구조는 Issue #7의 초기화 기준이다. 각 하위 패키지에는 3단계 구현 전까지 동작을 추가하지 않는다.

```text
src/tech_pilot/
  cli.py
  collection/
  sources/
  storage/
tests/
data/                 # Git 제외
```

초기 검증 명령은 `uv run ruff format --check`, `uv run ruff check`, `uv run mypy src`, `uv run pytest`다. 실제 실행 결과는 Issue #7의 PR에서 확인한다.

## Risks to Validate Before Phase 3

1. 후보 RSS·Atom 출처의 날짜·식별자·중복 URL 품질을 작은 fixture로 확인한다.
2. ETag·Last-Modified와 요청 timeout·재시도 정책의 최소 계약을 정한다.
3. 로컬 SQLite 파일을 사용하는 스케줄이 겹치지 않도록 실행 잠금과 백업 요구를 확인한다.
4. 공식 API·HTML 출처별 인증, 사용량 제한, robots·이용 정책을 수집 설계 전에 기록한다.

## Sources

- [Python `sqlite3` documentation](https://docs.python.org/3/library/sqlite3.html)
- [Python `argparse` documentation](https://docs.python.org/3/library/argparse.html)
- [uv documentation](https://docs.astral.sh/uv/)
- [HTTPX documentation](https://www.python-httpx.org/)
- [feedparser documentation](https://feedparser.readthedocs.io/en/latest/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [mypy documentation](https://mypy.readthedocs.io/en/stable/)
- [pytest documentation](https://docs.pytest.org/en/stable/)
