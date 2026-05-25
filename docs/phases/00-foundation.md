# Phase 00 Foundation

## 산출물

- `backend/`: uv 기반 FastAPI 프로젝트
  - `/health` 엔드포인트
  - Pydantic Settings
  - SQLAlchemy 2.x `Base`와 session factory
  - Alembic 기본 골격
  - 6개 고정 진단 도메인 모델
- `frontend/`: Next.js App Router 기반 내부 MVP 화면
  - TypeScript, Tailwind, ESLint 설정
  - shadcn/ui 호환 `components.json`과 alias 구조
  - Zod 기반 도메인/health 타입
  - 6개 진단 도메인과 API health 상태 렌더링
- `compose.yaml`: PostgreSQL 16, backend, frontend 로컬 통합 실행
- `.env.example`: 공통 환경 변수 예시
- `requirements.txt`: `backend/uv.lock`에서 `--no-emit-project`로 export한 호환용 산출물

## 검증 방법

```bash
uv --version
cd backend && uv sync --locked
cd backend && uv run python --version
cd backend && uv run pytest
cd backend && uv run ruff check
cd backend && uv run mypy src
cd frontend && npm ci
cd frontend && npm run lint
cd frontend && npm run build
docker info
docker run hello-world
docker compose config
docker compose up --build
curl http://localhost:8000/health
```

## 검증 결과

- `uv --version`: `uv 0.11.16`
- `cd backend && uv sync --locked`: 통과
- `cd backend && uv run python --version`: `Python 3.12.13`
- `cd backend && uv run pytest -q`: `1 passed`
- `cd backend && uv run ruff check`: 통과
- `cd backend && uv run mypy src`: 통과
- `cd frontend && npm ci`: 통과
- `cd frontend && npm run lint`: 통과
- `cd frontend && npm run build`: 통과
- `cd frontend && npm audit --omit=dev`: `found 0 vulnerabilities`
- `docker info`: Docker Engine 24.0.7 daemon 접근 확인
- `docker run hello-world`: 통과
- `docker compose config`: 통과
- `docker compose up --build --detach`: PostgreSQL, backend, frontend 빌드 및 기동 확인
- `curl http://localhost:8000/health`: 200 응답과 6개 진단 도메인 확인
- `curl http://localhost:3000`: 프론트엔드 HTML과 6개 진단 도메인 렌더링 확인

## 남은 리스크

- 프론트/백엔드 도메인 타입은 현재 중복 정의입니다. Phase 01 이후 codegen 또는 sync 정책을 결정합니다.
- 문항 스키마, seed 데이터, 진단 알고리즘, 검색 에이전트 외부 호출은 Phase 00 범위 밖입니다.
- `pgvector`는 기본 compose에 넣지 않았습니다. Phase 04에서 검색 요구가 확정되면 PostgreSQL 이미지/확장 정책을 재검토합니다.
