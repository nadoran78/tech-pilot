# Tech Pilot

Tech Pilot은 새롭게 등장하는 AI 기술을 지속적으로 파악하고, 장기적으로 사용자의 프로젝트·학습·수익화에 미치는 영향을 판단하는 개인 AI CTO 프로젝트다.

## Current Status

현재는 **4단계: 요약·분류 및 의미 기반 통합**을 진행하고 있다. 사용자가 2026-10-15에 단계 전환을 승인했고, 2026-10-18에 제목 기반 입력·출력, 평가 기준과 [ADR 0007](docs/decisions/0007-news-understanding-execution-storage.md)의 실행·저장·재실행안을 승인했다. 저장 기반에 이어 [네트워크 없는 제목 규칙 기준선](docs/specs/news-understanding-rules.md)을 구현했다. 수동 실행·조회 CLI와 실제 표본 품질 평가는 후속 작업이다. 모델·비용·유료 API·자동화·블로그 작성은 별도 결정·승인 대상이다.

- 프로젝트의 배경과 목표: [제품 비전](docs/product/vision.md)
- 전체 개발 단계: [제품 로드맵](docs/product/roadmap.md)
- 현재 단계의 범위: [4단계 문서](docs/phases/04-news-understanding.md)
- 전체 문서 지도: [문서 인덱스](docs/INDEX.md)

## For Contributors and Codex

저장소에서 작업하기 전에 [AGENTS.md](AGENTS.md)를 읽는다. 문서는 한 파일에 모든 내용을 모으지 않고, 필요한 맥락을 단계적으로 찾을 수 있도록 연결해 관리한다.

Issue, 브랜치와 PR 작업은 [개발 워크플로](docs/process/development-workflow.md)를 따른다.

## Local Development

Python 3.13과 [uv](https://docs.astral.sh/uv/)가 필요하다. 의존성을 설치한 뒤 다음 명령으로 기본 검증을 실행한다.

```bash
uv sync
uv run tech-pilot --help
uv run ruff format --check
uv run ruff check
uv run mypy src
uv run pytest
```

`data/`와 `.env` 파일은 로컬 전용이며 Git에 포함하지 않는다.
