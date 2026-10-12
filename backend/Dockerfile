FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PROJECT_ENVIRONMENT=/usr/local
COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

FROM base AS dev-deps
RUN uv sync --locked

FROM dev-deps AS test
COPY . .
# どのチェックで失敗したかをビルドログで判別しやすいよう、RUN を分ける
RUN ruff check .
RUN ruff format --check .
RUN mypy
RUN pytest --cov

FROM base AS production
COPY . .
# デプロイ時にコミット SHA を渡し、/health の version で稼働中のバージョンを確認できるようにする
ARG APP_VERSION=unknown
ENV APP_VERSION=$APP_VERSION
CMD ["uvicorn", "app.frameworks.asgi:app", "--host", "0.0.0.0", "--port", "8000"]
