# Phase 01 Question Writing Guide

## 목적

DDEP 문항은 단순 암기 퀴즈가 아니라 드론 개발 역량의 취약 개념을 찾기 위한 진단 데이터입니다. 각 문항은 실제 설계 판단, 트러블슈팅, 운영 의사결정과 연결되어야 합니다.

## 고정 도메인

문항 `domain`은 백엔드 `DiagnosisDomain`의 여섯 값 중 하나만 사용합니다.

| Domain | Label |
| --- | --- |
| `airframe_aerodynamics` | 기체/공력 |
| `electronics_hardware` | 전장/하드웨어 |
| `control` | 제어 |
| `software` | 소프트웨어 |
| `autonomous_ai` | 자율비행/AI |
| `fabrication_operations` | 제작/운용 |

수학/물리 기초는 별도 도메인으로 만들지 않습니다. 필요한 경우 `basic_physics`, `coordinate_frames`처럼 concept tag 또는 prerequisite tag로 연결합니다.

## Seed 구조

Seed 파일은 `concept_tags`와 `questions`를 top-level 필드로 둡니다. Tag slug는 lower snake_case ASCII만 허용합니다.

문항 필수 필드:

- `external_id`: seed 안에서 안정적인 고유 ID
- `domain`, `subdomain`
- `difficulty`: `easy`, `medium`, `hard`
- `answer_type`: `single_choice`, `multi_select`, `short_answer`
- `review_status`: `draft`, `in_review`, `approved`, `deprecated`
- `source_type`: `official_docs`, `technical_manual`, `course_material`, `paper`, `internal_note`, `expert_review`
- `source_title`, `source_url`, `source_reference`
- `concept_tags`: 하나 이상
- `prerequisites`: approved 문항은 하나 이상
- `prompt`, `explanation`
- 객관식은 `choices`, 단답형은 `accepted_answers`

## 답안 규칙

- `single_choice`: 선택지 2개 이상, 정답은 정확히 1개
- `multi_select`: 선택지 3개 이상, 정답은 2개 이상
- `short_answer`: 선택지 없음, `accepted_answers`는 하나 이상
- 단답형은 trim + Unicode NFKC normalization + 기본 casefold 후 exact match만 허용합니다.
- regex, semantic/freeform, LLM grading은 Phase 01 production seed에서 금지합니다.

## Review 규칙

`approved` 문항은 다음을 만족해야 합니다.

- 출처 타입, 제목, reference가 비어 있지 않음
- concept tag와 prerequisite tag가 모두 seed manifest에 존재함
- prerequisites가 비어 있지 않음
- explanation이 왜 정답인지 설명함
- 도메인별 분포 기준을 깨지 않음

Draft 문항에서 빈 prerequisites를 임시 허용하거나 production 분포 기준을 아직 만족하지 않는 draft-only seed를 확인하려면 local/dev 용도로만 `--include-drafts`를 사용합니다.

## CLI

```bash
cd backend
uv run python -m ddep_backend.question_db validate seeds/phase01_questions.json
uv run python -m ddep_backend.question_db import seeds/phase01_questions.json
```

검증 실패 시 CLI는 nonzero로 종료하고 수정 가능한 오류 목록을 출력합니다.
