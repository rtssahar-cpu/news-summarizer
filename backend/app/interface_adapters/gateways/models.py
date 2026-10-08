from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.frameworks.database import Base


class ArticleModel(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(2048), unique=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    summary: Mapped["SummaryModel | None"] = relationship(back_populates="article", uselist=False)


class SummaryModel(Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), unique=True)
    summary_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    article: Mapped["ArticleModel"] = relationship(back_populates="summary")
