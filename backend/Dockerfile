FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

FROM base AS dev-deps
COPY requirements-dev.txt .
RUN uv pip install --system --no-cache -r requirements-dev.txt

FROM dev-deps AS test
COPY . .
RUN ruff check . && pytest

FROM base AS production
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
