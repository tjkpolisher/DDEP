FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

RUN uv sync --frozen --no-dev --no-cache

EXPOSE 8000

CMD ["uv", "run", "--frozen", "uvicorn", "ddep_backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
