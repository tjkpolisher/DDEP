# AGENTS.md - DDEP: Drone Diagnosis and Education Platform

이 문서는 드론 개발 역량 진단 플랫폼의 루트 작업 규칙입니다.
Phase별 세부 규칙은 `phases/*/AGENTS.md`를 우선 확인하세요.

## 1. 제품 기준

- MVP 1차 사용자는 팀 내부자 및 가까운 베타 그룹입니다.
- 제품 목표는 단순 퀴즈가 아니라 드론 개발 역량 지도, 취약 개념, 학습 로드맵을 제공하는 것입니다.
- 진단 도메인은 다음 6개로 고정합니다.
  - 기체/공력
  - 전장/하드웨어
  - 제어
  - 소프트웨어
  - 자율비행/AI
  - 제작/운용
- 수학/물리 기초는 독립 도메인으로 만들지 않습니다. 필요한 경우 각 도메인의 선행 개념 태그로만 둡니다.
- 검색 에이전트 구현은 MVP 범위에 포함합니다.
- 문항 DB 구축은 별도 Phase로 분리합니다.

## 2. 기술 스택 기준

- Frontend: Next.js + TypeScript + Tailwind + shadcn/ui
- Backend: FastAPI + Python
- Package manager: `uv`
- DB: PostgreSQL
- Vector search: 필요 시 pgvector
- Cache/Queue: MVP에서는 선택 사항입니다. 검색 에이전트 비동기화가 필요해질 때 Redis + RQ 또는 Celery를 검토합니다.
- Auth: 내부 MVP에서는 단순 계정 또는 초대 기반 접근을 우선합니다.
- Infra: Docker Compose 기준으로 로컬 재현성을 먼저 확보합니다.

## 3. 작업 원칙

- 구현 전에 현재 Phase의 `AGENTS.md`와 관련 문서를 읽습니다.
- Phase 범위를 넘어서는 기능은 TODO로 남기고 현재 Phase 산출물을 먼저 완성합니다.
- 도메인, 문항, 진단 결과, 추천 자료는 모두 구조화된 데이터로 다룹니다.
- 임시 문자열 파싱보다 Pydantic 모델, SQLAlchemy 모델, Zod 스키마 등 명시적 스키마를 우선합니다.
- Python 의존성 추가/실행은 `uv add`, `uv sync`, `uv run` 흐름을 사용합니다.
- 외부 웹/API 호출이 필요한 검색 에이전트 작업은 호출 경로와 실패 정책을 문서화합니다.

## 4. MVP 완료 조건

- 내부 사용자가 진단을 시작하고 15~30분 안에 6개 도메인 진단을 완료할 수 있습니다.
- 결과는 단일 총점이 아니라 도메인별 점수, 취약 concept tag, 다음 학습 순서로 표시됩니다.
- 검색 에이전트는 취약 concept tag를 기반으로 3~7개의 자료를 추천합니다.
- 추천 자료에는 추천 이유, 난이도, 신뢰도, 선행 개념이 포함됩니다.
- 사용자는 학습 후 동일 도메인 또는 취약 개념을 재진단할 수 있습니다.

## 5. 금지 사항

- MVP에서 결제/구독/수익화 기능을 만들지 않습니다.
- 검증되지 않은 검색 결과를 그대로 학습 추천으로 노출하지 않습니다.
- 문항 DB를 코드 상수에 하드코딩하지 않습니다.
- 수학/물리 기초를 별도 진단 도메인으로 확장하지 않습니다.
- LLM 주관식 채점을 MVP의 핵심 채점 경로로 두지 않습니다. 초기 MVP는 객관식/단답형 중심입니다.

## 6. Phase 진입 순서

1. `phases/00-foundation`
2. `phases/01-question-db`
3. `phases/02-diagnosis-engine`
4. `phases/03-result-report`
5. `phases/04-search-agent`
6. `phases/05-service-mvp`

각 Phase가 끝날 때는 산출물, 검증 방법, 남은 리스크를 `docs/phases/`에 기록합니다.

