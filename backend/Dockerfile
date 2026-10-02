FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/usr/local
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

FROM base AS dev-deps
RUN uv sync --locked

FROM dev-deps AS test
COPY . .
RUN ruff check . && pytest

FROM base AS production
COPY . .
CMD ["uvicorn", "app.frameworks.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
