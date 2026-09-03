# Tech Pilot

Tech Pilot은 새롭게 등장하는 AI 기술을 지속적으로 파악하고, 장기적으로 사용자의 프로젝트·학습·수익화에 미치는 영향을 판단하는 개인 AI CTO 프로젝트다.

## Current Status

현재는 **2단계: 기술 스택 선정**을 진행하고 있다. 뉴스 수집 MVP의 기술 스택 기준은 승인됐으며, Issue #7에서 3단계 구현을 위한 Python 프로젝트 골격을 초기화한다. 뉴스 수집 기능은 아직 구현하지 않는다.

- 프로젝트의 배경과 목표: [제품 비전](docs/product/vision.md)
- 전체 개발 단계: [제품 로드맵](docs/product/roadmap.md)
- 현재 단계의 범위: [2단계 문서](docs/phases/02-tech-stack-selection.md)
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
