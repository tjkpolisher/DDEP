# Phase 01 Question DB

## 산출물

- `backend/src/ddep_backend/question_db/`: 문항 DB enum, SQLAlchemy 모델, seed 검증, import CLI, deterministic short-answer grading helper
- `backend/migrations/versions/20260526_0326_phase01_question_db.py`: Phase 01 관계형 테이블 생성 migration
- `backend/seeds/phase01_questions.json`: 30개 approved v1 seed 문항
- `backend/tests/test_question_db_seed.py`: seed contract, validation, deterministic short-answer unit tests
- `backend/tests/test_question_db_integration.py`: disposable PostgreSQL migration/import/idempotency test
- `docs/phases/01-question-writing-guide.md`: 문항 작성 및 검수 가이드

## Schema Summary

- `questions`: question core, canonical domain, difficulty, answer type, review status, source metadata, prompt, explanation, short-answer accepted answers
- `question_choices`: ordered answer choices with stable `choice_key` and `sort_order`
- `concept_tags`: controlled concept/prerequisite tag manifest
- `question_concept_tags`: question-to-concept association
- `question_prerequisite_tags`: question-to-prerequisite association
- `concept_tag_prerequisites`: prerequisite chain between concept tags

`questions.external_id` and `concept_tags.slug` are unique. Association pair tables and choice ordering are constrained by unique pairs.

## Seed Distribution

| Domain | Approved Questions |
| --- | ---: |
| `airframe_aerodynamics` | 5 |
| `electronics_hardware` | 5 |
| `control` | 5 |
| `software` | 5 |
| `autonomous_ai` | 5 |
| `fabrication_operations` | 5 |

Each domain has at least three objective questions, at least one deterministic short-answer question, and difficulty coverage of easy >= 1, medium >= 2, hard >= 1.

## 검증 방법

```bash
cd backend && uv run python -m ddep_backend.question_db validate seeds/phase01_questions.json
cd backend && uv run pytest
cd backend && uv run ruff check
cd backend && uv run mypy src
```

Disposable PostgreSQL integration:

```bash
cd backend
DDEP_TEST_DATABASE_URL=postgresql+psycopg://ddep:ddep@localhost:5432/ddep_test uv run pytest
uv run python -m ddep_backend.question_db import seeds/phase01_questions.json
uv run python -m ddep_backend.question_db import seeds/phase01_questions.json
```

## 검증 결과

- `cd backend && uv run python -m ddep_backend.question_db validate seeds/phase01_questions.json`: `Seed valid: seeds/phase01_questions.json (30 approved questions)`
- `cd backend && uv run pytest`: `19 passed, 1 skipped`
- `cd backend && uv run ruff check`: 통과
- `cd backend && uv run mypy src`: 통과
- `cd backend && DDEP_TEST_DATABASE_URL=postgresql+psycopg://ddep:ddep@localhost:5432/ddep_test uv run pytest`: `20 passed`
- `cd backend && DDEP_DATABASE_URL=postgresql+psycopg://ddep:ddep@localhost:5432/ddep_test uv run python -m ddep_backend.question_db import seeds/phase01_questions.json`: 두 번 모두 `questions=30, choices=96, concept_tags=36, question_concept_tags=45, question_prerequisite_tags=39, concept_tag_prerequisites=31`
- Ralph architect verification: 승인
- Ralph deslop pass: changed files only, dead unused helper deleted, post-deslop regression 통과

## 남은 리스크

- 문항 내용은 MVP seed로 구조화되어 있으나 production 노출 전 도메인 전문가 검수가 필요합니다.
- Integration test는 `DDEP_TEST_DATABASE_URL`이 없으면 skip됩니다. 일반 `ddep` DB를 가리키면 fail-fast합니다.
- Source/review workflow는 MVP에 맞춰 `questions` 필드로 단순화했습니다. CMS/admin, source table 분리는 이후 사용 패턴이 쌓인 뒤 재검토합니다.
