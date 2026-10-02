import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def build_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)

    user = os.environ.get("POSTGRES_USER", "newssummarizer")
    password = os.environ.get("POSTGRES_PASSWORD", "newssummarizer")
    host = os.environ.get("POSTGRES_HOST", "db")
    port = os.environ.get("POSTGRES_PORT", "5432")
    name = os.environ.get("POSTGRES_DB", "newssummarizer")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


class Base(DeclarativeBase):
    pass


engine = create_engine(build_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
