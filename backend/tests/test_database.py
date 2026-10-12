import pytest

from app.frameworks.database import build_database_url

POSTGRES_ENV_KEYS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
)


def test_build_database_url_converts_database_url_to_psycopg_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@example.com:5432/app")

    assert build_database_url() == "postgresql+psycopg://user:pass@example.com:5432/app"


def test_build_database_url_uses_postgres_env_vars_when_database_url_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "alice")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    monkeypatch.setenv("POSTGRES_DB", "testdb")

    assert build_database_url() == "postgresql+psycopg://alice:secret@localhost:15432/testdb"


def test_build_database_url_falls_back_to_defaults_when_no_env_vars_are_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    for key in POSTGRES_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    assert (
        build_database_url()
        == "postgresql+psycopg://newssummarizer:newssummarizer@db:5432/newssummarizer"
    )
