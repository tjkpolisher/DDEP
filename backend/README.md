# DDEP Backend

FastAPI 기반 DDEP 백엔드입니다. Python 실행과 의존성 관리는 `uv`로 통일합니다.

## Commands

```bash
uv sync --locked
uv run fastapi dev src/ddep_backend/main.py
uv run pytest
uv run ruff check
uv run mypy src
```

기본 API는 `http://localhost:8000`에서 실행되며 health check는 `/health`입니다.
