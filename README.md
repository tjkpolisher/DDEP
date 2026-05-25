# DDEP, Drone Diagnosis and Education Platform

드론 개발 역량 진단 플랫폼 작업공간입니다.

## MVP 방향

- 대상: 팀원 및 가까운 베타 그룹
- 목적: 드론 개발 역량을 6개 도메인 기준으로 진단하고 학습 로드맵을 추천
- 범위: 진단, 결과 리포트, 검색 에이전트 기반 추천 자료까지 MVP에 포함
- 제외: 수학/물리 기초 독립 도메인, 결제, 팀 관리자 대시보드, 자체 강의 콘텐츠
- Python 패키지 관리는 `uv`를 사용

## 로컬 도구

- Python 패키지 관리자: `uv`
- Backend Python: `>=3.12,<3.15` (`backend/.python-version`)
- Frontend Node: `>=20.9` (현재 로컬 기준 Node 22 계열)
- Docker Compose: 로컬 DB, 백엔드, 프론트엔드 통합 실행 기준

`uv`가 없으면 사용자 환경에 먼저 설치합니다.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version
```

## 실행 경로

환경 변수 예시는 `.env.example`에 있습니다. 필요한 경우 루트에 `.env`를 만들고 값을 조정합니다.

### Backend

```bash
cd backend
uv sync --locked
uv run fastapi dev src/ddep_backend/main.py
```

검증:

```bash
cd backend
uv run pytest
uv run ruff check
uv run mypy src
```

Health check:

```bash
curl http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

검증:

```bash
cd frontend
npm run lint
npm run build
```

프론트엔드는 기본적으로 `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`을 사용합니다.

### Docker Compose

```bash
docker compose config
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

Docker가 없거나 daemon 접근이 실패하면 Docker Engine과 Compose plugin을 먼저 설치/활성화합니다.
Phase 00 기본 DB 이미지는 `postgres:16`이며, `pgvector`는 Phase 04 검색 에이전트에서 재검토합니다.

## 의존성 잠금

- 백엔드 정본: `backend/pyproject.toml`, `backend/uv.lock`
- 프론트엔드 정본: `frontend/package.json`, `frontend/package-lock.json`
- 루트 `requirements.txt`: `backend/uv.lock`에서 export한 호환용 산출물

`requirements.txt`를 갱신할 때:

```bash
cd backend
uv export --frozen --no-dev --no-editable --no-emit-project --output-file ../requirements.txt
```

## 공통 타입 위치

- Backend: `backend/src/ddep_backend/domains.py`, `backend/src/ddep_backend/schemas/health.py`
- Frontend: `frontend/src/lib/domains.ts`, `frontend/src/lib/health.ts`

Phase 00에서는 6개 진단 도메인과 health 응답 모델만 둡니다. 문항 스키마, seed 데이터, 진단 알고리즘, 검색 호출은 Phase 01 이후에서 다룹니다.

## Phase 구조

1. `phases/00-foundation`: 프로젝트 기본 동작, 스택, 공통 규칙
2. `phases/01-question-db`: 문항 DB 구축
3. `phases/02-diagnosis-engine`: 진단 엔진
4. `phases/03-result-report`: 결과 리포트
5. `phases/04-search-agent`: 검색 에이전트
6. `phases/05-service-mvp`: 서비스화 MVP
