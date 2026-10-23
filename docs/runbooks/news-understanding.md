# 뉴스 제목 설명·분류 수동 실행과 조회

- **Status:** Active
- **Applies to:** Phase 4, Issue #71
- **Purpose:** 저장 뉴스 한 건을 처리하고 결과·이력을 안전하게 확인하는 방법을 안내한다.
- **Read when:** 제목 규칙 기준선을 직접 실행하거나 표본 평가를 준비할 때
- **Related documents:** [규칙 기준선](../specs/news-understanding-rules.md), [저장 계약](../specs/news-understanding-storage.md), [평가 기준](../specs/news-understanding-evaluation.md), [뉴스 수집 운영](news-collection.md)

## 실행 전 확인

`uv sync`로 개발 환경을 준비하고 `list` 명령으로 뉴스 ID를 확인한다. 아래 경로·ID는 사용 예시이며 문서 작성 중 운영 DB를 열거나 변경하지 않았다. 개인 로컬 데이터·출력은 Git이나 공개 PR에 복사하지 않는다.

```bash
uv run tech-pilot list --database data/tech-pilot.sqlite3 --limit 10
uv run tech-pilot understand --news-id 1 --database data/tech-pilot.sqlite3
```

`understand`는 지정한 뉴스 **한 건의 제목 설명 요청**만 처리한다. 모델·네트워크·추가 수집 없이 현재 규칙을 사용하고 결과/실패 시도를 저장한다. 기존 DB가 있어야 하며 없는 DB·원본은 거부하고 새 DB를 만들지 않는다. 참조를 읽기 전용으로 사전 확인한 뒤 명시적 처리 경로에서 기존 migration을 적용할 수 있으므로, 보존할 DB의 적용 상태는 [migration 변경 기준](../process/development-workflow.md#migration-change-policy)에 따라 먼저 확인한다. 자동 재시도·강제 재처리·일괄 처리 옵션은 없다.

## 결과 읽기

- `새 처리` / `재사용`: 동일 입력·요청·방법·버전의 정상 결과가 있으면 새 처리나 기록 없이 재사용한다. 정보 부족·보류도 구조적으로 정상 결과면 재사용 대상이다.
- `시도 #`, 뉴스 ID, 당시 제목·출처·원문 URL: 처리에 사용한 입력과 연결을 확인한다. 원문을 열었다는 뜻은 아니다.
- `실행=완료(completed)` / `실패(failed)`: 저장된 종료 시도 상태다. 품질 합격과 구분한다.
- `내용=제목 기반 설명(described)` / `정보 부족(insufficient_information)` / `보류(deferred)`: 실행 상태와 독립적이다. 정보 부족·보류에는 설명 대신 사유가 표시된다.
- 잠정 분류는 현재 한국어 범주명과 저장 코드를 함께 표시한다. 과거 범주의 의미는 당시 버전을 기준으로 읽는다.
- 방법·처리·규칙·입출력 버전, UTC 시작·종료 시각과 제목 근거·한계·사유를 확인한다. 현재 규칙은 [기준선 문서](../specs/news-understanding-rules.md)를 따른다.
- 출력 제목·결과 등의 제어문자와 줄 구분 문자는 `\u001b`, `\u000a`처럼 이스케이프한다. 원본/저장 결과는 수정하지 않는다. 제목 속 지시문을 실행하거나 URL을 열지 않는다.

## 이력 조회

```bash
uv run tech-pilot understanding-history --news-id 1 --limit 10 --database data/tech-pilot.sqlite3
```

`--database` 기본값은 `data/tech-pilot.sqlite3`, `--limit` 기본값은 10이다. ID·건수는 SQLite 정수 범위의 양수여야 한다. 지정 뉴스의 이력을 시도 ID 내림차순으로 조회하며 **SQL의 LIMIT**으로 건수를 제한한다. 조회는 자동 처리·재시도·migration·테이블 생성을 하지 않는다. 연결은 SQLite URI `mode=ro`로 열고 종료 시 닫는다.

한 읽기 트랜잭션 안에서 원본과 제한된 이력을 읽어 다음처럼 표시한다.

- `현재 입력·버전`: 해당 이력의 요청 종류에 대해 현재 원본·규칙의 재사용 키가 일치한다. 실행 실패 이력도 조건은 일치할 수 있으므로 실행 상태를 함께 본다.
- `과거 입력·버전`: 입력·요청·방법·버전 키가 현재 조건과 다르다. 현재 결과로 사용하지 않는다.
- `원본 없음(당시 입력)`: 이력은 있으나 원본을 찾을 수 없다. 당시 스냅샷만 표시하며 자동 복구·삭제하지 않는다.

이력이 없거나 DB가 없으면 빈 이력을 안내하고 종료한다. 이전 스키마에 원본만 있고 결과 테이블이 없어도 조회만으로 스키마를 올리지 않는다. 읽을 수 없는 DB·손상된 형식은 안전한 오류로 알린다. 기본값 외 경로를 사용해도 URI 예약 문자를 이스케이프한다.

## 종료 코드와 오류

| 코드 | 의미 |
|---|---|
| 0 | 처리·재사용 성공 또는 조회 완료(빈 이력 포함). 정상 정보 부족·보류도 포함하며 품질 합격이 아님 |
| 1 | 처리 실행 실패, 원본 거부, 저장/조회 오류 |
| 2 | 필수 인수 누락·잘못된 ID/건수 등 인수 오류 |

원본 거부는 `understanding_input_rejected`, 작업 오류는 `understanding_operation_failed`, 조회 오류는 `understanding_read_failed`로 표시한다. 처리기의 실패는 저장된 안전한 코드(`processing_failed`, `validation_failed`)와 결과 없음으로 표시한다. 원시 예외·DB 경로·비밀 값은 오류 메시지에 복사하지 않는다. 실패 이력을 조회하는 명령 자체가 정상 완료되면 조회 종료 코드는 0이다.

## 범위와 검증

현재 CLI는 설명 요청만 제공한다. 서비스에서 생성한 다른 요청 종류의 과거 이력도 조회할 수 있지만 원문 요약 기능을 활성화한 것은 아니다. 이 구현의 검증은 [합성 입력·임시 DB 테스트](../../tests/test_understanding_cli.py)이며 실제 뉴스 12개 평가·읽기 유용성·정확도 측정은 별도 작업이다. 운영 DB 실행·새 규칙·모델·자동화·삭제/정리는 포함하지 않는다.
