# Phase 02 Diagnosis Engine

## 산출물

- `backend/src/ddep_backend/diagnosis_engine/`: deterministic backend diagnosis engine package
- `backend/src/ddep_backend/diagnosis_engine/models.py`: engine DTOs for questions, submitted answers, outcomes, session state, scores, concept mastery, weak concepts, and results
- `backend/src/ddep_backend/diagnosis_engine/engine.py`: grading, Bayesian-lite scoring, prerequisite traversal, session updates, explicit completion, and adaptive candidate selection
- `backend/src/ddep_backend/diagnosis_engine/repository.py`: Phase 01 SQLAlchemy question DB adapter
- `backend/tests/test_diagnosis_engine.py`: grading, scoring, state, prerequisite, weak concept, and adaptive selection tests
- `backend/tests/test_diagnosis_engine_repository.py`: repository mapping test and optional disposable PostgreSQL seed-backed engine test

## Algorithm Summary

Phase 02 uses `bayes-lite-v1`.

- Prior: `alpha=1.0`, `beta=1.0`
- Difficulty weights: `easy=0.8`, `medium=1.0`, `hard=1.2`
- Score: `round(100 * (alpha + weighted_correct) / (alpha + beta + weighted_attempts))`
- Confidence: `min(1.0, evidence_weight / 3.0)`
- Weak concept threshold: score below `60` with evidence weight at least `1.0`

Domain evidence counts each answered question once. Concept evidence counts each concept tag on the answered question once. Question prerequisite tags are used for explanation and candidate selection, but are not directly counted as score evidence unless also present as concept tags.

## Engine Contract

- `grade_submitted_answer()` grades `single_choice`, `multi_select`, and `short_answer` deterministically.
- `apply_outcome()` records outcomes and rebuilds consecutive-correct counters without double-counting a re-answer.
- `calculate_result()` returns all six domain scores even when no answers exist.
- `build_prerequisite_chain()` performs sorted, deduplicated, cycle-safe prerequisite traversal.
- `select_next_candidates()` excludes answered and non-approved questions, then ranks candidates by adaptive priority.
- `complete_session()` is the only function that changes session status to `completed`.

Adaptive priority order:

1. Last wrong answer's prerequisite-linked candidate
2. Difficulty escalation after at least two consecutive correct answers
3. Adjacent deeper concept when a direct prerequisite is mastered
4. Lowest-confidence weak concept candidate
5. Deterministic coverage fallback

## Repository Adapter

`load_approved_engine_questions()` maps only `ReviewStatus.APPROVED` rows into `EngineQuestion` DTOs. It eagerly loads choices, concept tags, and prerequisite tags, preserving choice order and sorting tag slugs for deterministic behavior.

`load_concept_prerequisite_graph()` maps concept prerequisites as:

```text
concept_slug -> sorted prerequisite_slugs
```

## Scope Exclusions

- No FastAPI diagnosis routes
- No frontend or result-report UI
- No persisted diagnosis session/response tables
- No auth/history/recommendation workflow
- No new dependency
- No LLM scoring

## 검증 방법

```bash
cd backend && uv run pytest
cd backend && uv run ruff check
cd backend && uv run mypy src
```

Optional disposable PostgreSQL integration:

```bash
cd backend
DDEP_TEST_DATABASE_URL=postgresql+psycopg://ddep:ddep@localhost:5432/ddep_test uv run pytest
```

## 검증 결과

- `cd backend && uv run pytest`: `34 passed, 2 skipped`
- `cd backend && uv run ruff check`: 통과
- `cd backend && uv run mypy src`: 통과
- PostgreSQL integration tests were skipped because `DDEP_TEST_DATABASE_URL` was not set.

## 남은 리스크

- `bayes-lite-v1` is intentionally explainable and deterministic, not a full psychometric calibration model.
- Optional PostgreSQL verification depends on a disposable test database URL.
- Phase 03 may add presentation-oriented report fields on top of `DiagnosisResult`.
- Phase 05 should add persisted session/response tables and API workflow around this internal engine contract.
