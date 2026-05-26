# Phase 05 Service MVP

## 산출물
- Invite code + opaque bearer token access flow: `POST /access/verify`.
- Authenticated diagnosis lifecycle APIs: create, fetch, answer save, complete, results, recommendations, comparison.
- SQLAlchemy persistence for internal users, invite codes, access sessions, diagnosis sessions, answers, outcomes, result snapshots, recommendation runs/items, and ops events.
- Alembic migration `20260526_1050_phase05_service_mvp.py`.
- Frontend internal MVP workflow: invite verification, diagnosis start, answer save, completion, persisted report/recommendation rendering.

## API 개요
- `POST /access/verify`
- `POST /diagnoses`
- `GET /diagnoses/{id}`
- `POST /diagnoses/{id}/answers`
- `POST /diagnoses/{id}/complete`
- `GET /diagnoses/{id}/results`
- `GET /diagnoses/{id}/recommendations`
- `GET /diagnoses/{id}/comparison?previous_id=...`
- `GET /ops/events`

All diagnosis and ops APIs except `/access/verify` require `Authorization: Bearer <token>`.

## 운영 메모
- Invite codes are stored hashed with `DDEP_ACCESS_TOKEN_SECRET`; seed them through SQL or a small internal admin script before beta use.
- Completion loads approved questions, applies Phase 02 scoring, builds Phase 03 reports, runs Phase 04 recommendations, persists snapshots/items, and logs lifecycle/fallback events.
- Answer resubmission updates the stored answer/outcome for the same question instead of creating duplicate scoring evidence.

## 검증 방법
- `uv run pytest tests/test_service_mvp.py`
- 전체 gate: `uv run pytest`, `uv run ruff check`, `uv run mypy src`, `npm run lint`, `npm run build`

## 남은 리스크
- Invite code provisioning is documented but not exposed as an operator UI.
- Access tokens are opaque bearer tokens with DB-backed expiry; production rotation/revocation policy needs a separate ops decision before wider rollout.
- The frontend MVP currently steps through the first loaded question; richer multi-question navigation can build on the persisted answer APIs.
