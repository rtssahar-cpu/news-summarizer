import logging
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup, Tag

from app.use_cases.errors import SourceStructureChangedError

MOD_BASE_URL = "https://www.mod.go.jp"

logger = logging.getLogger(__name__)


@dataclass
class ModNotice:
    published_at: datetime
    title: str
    article_url: str
    pdf_url: str | None


def parse_mod_notice_list(html: str, reference_date: datetime) -> list[ModNotice]:
    soup = BeautifulSoup(html, "html.parser")
    notices: list[ModNotice] = []

    for item in soup.select("div.news__item"):
        date_tag = item.select_one("dt.date")
        title_tag = item.select_one("dd.news__title a")
        if date_tag is None or title_tag is None:
            continue

        article_href = title_tag.get("href")
        if not isinstance(article_href, str):
            continue

        date_text = date_tag.get_text(strip=True)
        try:
            published_at = _parse_date(date_text, reference_date)
        except ValueError:
            logger.warning("日付の形式が不正なためお知らせをスキップ: %r", date_text)
            continue

        pdf_url = _extract_pdf_url(item)
        notices.append(
            ModNotice(
                published_at=published_at,
                title=title_tag.get_text(strip=True),
                article_url=MOD_BASE_URL + article_href,
                pdf_url=pdf_url,
            )
        )

    if not notices:
        raise SourceStructureChangedError(
            source="mod", reason="お知らせ一覧ページからお知らせを1件も抽出できません"
        )
    return notices


def _extract_pdf_url(item: Tag) -> str | None:
    pdf_tag = item.select_one('a[href$=".pdf"]')
    if pdf_tag is None:
        return None
    pdf_href = pdf_tag.get("href")
    return MOD_BASE_URL + pdf_href if isinstance(pdf_href, str) else None


def _parse_date(text: str, reference_date: datetime) -> datetime:
    month, day = (int(part) for part in text.split("/"))
    candidate = reference_date.replace(
        month=month, day=day, hour=0, minute=0, second=0, microsecond=0
    )
    if candidate > reference_date:
        candidate = candidate.replace(year=candidate.year - 1)
    return candidate
