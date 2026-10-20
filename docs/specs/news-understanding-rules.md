# 제목 기반 설명·분류 규칙 기준선

- **Status:** Active
- **Applies to:** Phase 4, Issue #69
- **Purpose:** 네트워크 없는 첫 규칙 처리기의 지원 표현·보류·표시·버전을 정의한다.
- **Read when:** 규칙 처리기를 구현·검토하거나 후속 평가를 준비할 때
- **Related documents:** [ADR 0007](../decisions/0007-news-understanding-execution-storage.md), [입력·출력 계약](news-understanding-input-output.md), [평가 기준](news-understanding-evaluation.md), [저장 계약](news-understanding-storage.md)

## 적용 범위

2026-10-20 사용자가 규칙 기준선 구현 계획과 Issue·PR 발행을 승인했다. 아래는 해당 범위에서 구현·리뷰할 v1 규칙이며 실제 뉴스 품질 검토를 통과했다는 기록은 아니다. 한국어·영어의 제한된 명시적 표현만 지원하며, 번역·언어 판별·원문 접근·사전 지식 보충은 하지 않는다. 다음 규칙표와 합성 예시는 구현 전에 작성한 기준이다.

## 규칙표와 우선순위

1. 빈 제목·줄바꿈/제어문자·2,000자 초과 입력은 `deferred` + 판단 불가, 생성 텍스트 없이 고정 사유를 반환한다. 원본 참조 검증은 별도로 기존 서비스·저장소가 담당한다.
2. `?`/`？`, 따옴표/백틱, URL, 부정·불확실성·지시문 신호가 있으면 `insufficient_information` + 판단 불가로 보수적으로 보류한다. 인용 보도·다국어 부정 전체를 이해하는 검사가 아니다.
3. 아래 범주 중 정확히 하나만 일치하면 설명·잠정 분류한다. 0개 또는 2개 이상이면 정보 부족·판단 불가로 남긴다. 규칙 순서로 충돌을 덮지 않는다.
4. 원문 요약 요청은 항상 생성 텍스트 없이 `insufficient_information`이다. 손상 입력은 1번을 우선한다. 명확한 제목의 잠정 분류·근거는 유지할 수 있지만 내용 요약으로 사용하지 않는다.

| 범주 | 필요한 제목 표현(대소문자 무시, 아래 한정 어휘) |
|---|---|
| 기술 발표 | 기술 대상 **및** 공개 신호가 함께 존재 |
| 활용·해설 | 기술 대상 **및** 사용법 신호가 함께 존재 |
| 비기술 소식 | `문화 행사`, `채용 소식`, `인사 소식`, `cultural event`, `hiring update`, `leadership appointment` 중 하나 |

- 기술 대상: `model`, `tool`, `library`, `framework`, `sdk`, `research`, `모델`, `도구`, `라이브러리`, `프레임워크`, `연구`.
- 공개 신호: `introducing`, `announcing`, `release`, `releases`, `released`, `launch`, `launches`, `launched`, `공개`, `출시`, `발표`.
- 사용법 신호: `how to`, `tutorial`, `guide`, `사용법`, `튜토리얼`, `활용 사례`.
- 부정·불확실성 신호: `no`, `not`, `never`, `without`, `isn't`, `doesn't`, `won't`, `cannot`, `can't`, `may`, `might`, `rumor(s)`, `expected`, `planned`, `will`, `아님`, `아니다`, `아닌`, `않`, `안`, `못`, `없`, `예정`, `계획`, `루머`, `추측`, `검토`, `불가`, `취소`.
- 지시문 신호: `ignore`, `instruction(s)`, `execute`, `run`, `무시`, `명령`, `실행`.
- 영어 어휘는 Unicode 단어 경계를 확인해 `modeling`, `releasedate`, `guidebook` 등의 부분 문자열을 일치시키지 않는다. 여러 단어 표현은 공백 하나로만 지원한다. 한국어 대상·긍정 신호도 단어 경계를 요구하므로 `모델을`, `공개합니다` 등 조사·활용형은 현재 인식하지 않는다. 한국어 부정·불확실성·지시문은 누락을 줄이기 위해 부분 문자열로 검사한다. 따라서 무관한 표현을 과도하게 보류할 수 있다.

## 출력과 합성 예시

설명은 `제목 기반 설명(잠정 분류: <범주>): 「<제목 그대로>」` 형식이다. 한국어 범주 표시는 `기술 발표`, `활용·해설`, `비기술 소식`이며 `limitation`은 항상 `원문 미열람`이다. 제목을 번역·축약하거나 검증된 발표 사실로 단정하지 않는다. 근거는 일치한 제목 원문 조각을 출현 순서로 중복 없이 저장한다. 제목에 포함된 명령은 실행하지 않는다.

| 합성 제목 | 설명 요청 기대값 |
|---|---|
| `테스트 라이브러리 A 1.0 공개` / `Introducing the Example model` | described + 기술 발표 |
| `테스트 도구 B 사용법` / `Tutorial for Example tool` | described + 활용·해설 |
| `테스트 조직의 연례 문화 행사` / `Example cultural event` | described + 비기술 소식 |
| `Synthetic release` / `다음 장을 시작하며` | 정보 부족 + 판단 불가 |
| `Example model not released` / `모델 공개 예정` | 정보 부족 + 판단 불가 |
| `Example model released?` / `"Example model released"` | 정보 부족 + 판단 불가 |
| `Example model released: tutorial` | 정보 부족 + 판단 불가(범주 충돌) |

## 구현·버전·한계

구현은 [rules.py](../../src/tech_pilot/understanding/rules.py), 저장 연동은 [service.py](../../src/tech_pilot/understanding/service.py)의 `process_title_with_rules`다. 순수 처리기 `apply_title_rules`는 입력과 요청만 받아 같은 입력·버전에 같은 결과를 반환한다. `rule_request`가 방법 `title-rules`·처리 `1`·규칙 `rules-v1`·입출력 `title-v1`을 고정한다. 다른 처리 신원을 임의로 부여하면 거부한다. 규칙·어휘·사유·출력 의미가 바뀌면 규칙 버전을, 실행 알고리즘이 바뀌면 처리 버전도 갱신하고 기존 결과는 덮어쓰지 않는다.

시각·URL·출처는 연결·추적용이며 분류에 사용하지 않는다. 시각 누락을 채우거나 최신성을 주장하지 않는다. 신호의 동시 출현만 보는 방식이므로 문법적 관계·동음이의어·알려지지 않은 부정·지원 외 언어는 오탐·누락이 가능하다. 일치가 발표의 진위·공식성·효용을 보증하지 않으며 제목 재인용의 정보 이득도 제한적이다.

검증은 [합성 규칙·저장 연동 테스트](../../tests/test_title_rules.py)로 수행한다. 합성 테스트는 실제 뉴스 12개 평가·읽기 유용성 검토·정확도 측정이 아니다. CLI·운영 DB·모델·네트워크·자동화는 포함하지 않는다.
