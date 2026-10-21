from datetime import UTC, datetime

from app.entities.article import Article
from app.entities.article_analysis import ISRAEL_MENTION_CRITERION, PRICE_MENTION_CRITERION
from app.entities.category import CATEGORY_CRITERIA, Category
from app.interface_adapters.gateways.article_analysis_prompt import (
    JST,
    SUMMARY_ITEMS,
    build_system_prompt,
    build_user_message,
)


def make_article(published_at: datetime) -> Article:
    return Article(
        id=None,
        source="mhi",
        url="https://www.mhi.com/jp/news/261016.html",
        title="防衛装備庁と契約を締結",
        body="三菱重工業は、防衛装備庁と契約を締結した。",
        published_at=published_at,
    )


def test_system_prompt_lists_every_category_code_with_its_criterion() -> None:
    prompt = build_system_prompt()

    assert all(
        f"- {category.value}: {criterion}" in prompt
        for category, criterion in CATEGORY_CRITERIA.items()
    )


def test_system_prompt_contains_flag_criteria_and_summary_items() -> None:
    prompt = build_system_prompt()

    assert PRICE_MENTION_CRITERION in prompt
    assert ISRAEL_MENTION_CRITERION in prompt
    assert all(f"- {item}" in prompt for item in SUMMARY_ITEMS)


def test_system_prompt_is_deterministic() -> None:
    # プロンプトキャッシュを後から導入できるよう、呼び出しごとに内容が変わらないことを保証する
    assert build_system_prompt() == build_system_prompt()


def test_system_prompt_mentions_output_field_names() -> None:
    prompt = build_system_prompt()

    for field_name in ("matched_categories", "mentions_price", "mentions_israel", "summary_text"):
        assert field_name in prompt


def test_user_message_wraps_article_fields_in_tags() -> None:
    message = build_user_message(make_article(datetime(2026, 10, 16, 15, 0, tzinfo=JST)))

    assert "<title>防衛装備庁と契約を締結</title>" in message
    assert "<published_date>2026-10-16</published_date>" in message
    assert "<url>https://www.mhi.com/jp/news/261016.html</url>" in message
    assert "<body>\n三菱重工業は、防衛装備庁と契約を締結した。\n</body>" in message


def test_user_message_uses_japan_date_for_utc_datetime() -> None:
    # 日本時間 2026-10-16 00:00 は UTC では前日の 15:00
    article = make_article(datetime(2026, 10, 15, 15, 0, tzinfo=UTC))

    assert "<published_date>2026-10-16</published_date>" in build_user_message(article)


def test_category_codes_in_prompt_are_valid_category_values() -> None:
    codes = [
        line.removeprefix("- ").split(":")[0]
        for line in build_system_prompt().splitlines()
        if line.startswith("- ") and ":" in line
    ]

    assert {Category(code) for code in codes} == set(Category)
