import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from anthropic.types import Message

from app.entities.article import Article
from app.entities.category import Category
from app.interface_adapters.gateways.claude_article_analyzer import (
    MAX_BODY_LENGTH,
    MODEL,
    ClaudeArticleAnalyzer,
)
from app.use_cases.errors import ArticleAnalysisUnavailableError

VALID_OUTPUT = {
    "summary_text": "概要: 防衛装備庁と契約を締結した。",
    "matched_categories": ["contractor_mitsubishi_heavy", "standoff_missile"],
    "mentions_price": True,
    "mentions_israel": False,
}


def make_article(body: str = "三菱重工業は、防衛装備庁と契約を締結した。") -> Article:
    return Article(
        id=None,
        source="mhi",
        url="https://www.mhi.com/jp/news/261016.html",
        title="防衛装備庁と契約を締結",
        body=body,
        published_at=datetime(2026, 10, 16, tzinfo=UTC),
    )


def make_response(text: str, stop_reason: str = "end_turn") -> Message:
    return Message.model_validate(
        {
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": MODEL,
            "content": [
                {"type": "thinking", "thinking": "", "signature": "sig"},
                {"type": "text", "text": text},
            ],
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": {"input_tokens": 3000, "output_tokens": 500},
        }
    )


def make_analyzer(response: Message) -> tuple[ClaudeArticleAnalyzer, MagicMock]:
    client = MagicMock()
    client.messages.create.return_value = response
    return ClaudeArticleAnalyzer(client), client


def test_analyze_returns_analysis_from_structured_output() -> None:
    analyzer, client = make_analyzer(make_response(json.dumps(VALID_OUTPUT)))

    analysis = analyzer.analyze(make_article())

    assert analysis.matched_categories == (
        Category.CONTRACTOR_MITSUBISHI_HEAVY,
        Category.STANDOFF_MISSILE,
    )
    assert analysis.mentions_price is True
    request: dict[str, Any] = client.messages.create.call_args.kwargs
    assert request["model"] == MODEL
    assert request["output_config"]["effort"] == "medium"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert "<title>防衛装備庁と契約を締結</title>" in request["messages"][0]["content"]


def test_analyze_skips_article_whose_body_is_too_long_without_calling_api() -> None:
    analyzer, client = make_analyzer(make_response(json.dumps(VALID_OUTPUT)))

    with pytest.raises(ArticleAnalysisUnavailableError, match="本文が長すぎます"):
        analyzer.analyze(make_article(body="あ" * (MAX_BODY_LENGTH + 1)))
    client.messages.create.assert_not_called()


def test_analyze_accepts_body_at_the_length_limit() -> None:
    analyzer, _ = make_analyzer(make_response(json.dumps(VALID_OUTPUT)))

    assert analyzer.analyze(make_article(body="あ" * MAX_BODY_LENGTH)).is_defense_related


@pytest.mark.parametrize(
    ("stop_reason", "message"),
    [("refusal", "拒否されました"), ("max_tokens", "出力上限に達しました")],
)
def test_analyze_skips_article_when_response_stops_abnormally(
    stop_reason: str, message: str
) -> None:
    analyzer, _ = make_analyzer(make_response('{"summary_text": "概要', stop_reason))

    with pytest.raises(ArticleAnalysisUnavailableError, match=message):
        analyzer.analyze(make_article())


@pytest.mark.parametrize(
    "text",
    ["応答がJSONではない", json.dumps({**VALID_OUTPUT, "summary_text": "  "})],
)
def test_analyze_skips_article_when_output_cannot_be_converted(text: str) -> None:
    analyzer, _ = make_analyzer(make_response(text))

    with pytest.raises(ArticleAnalysisUnavailableError, match="応答を解析できません"):
        analyzer.analyze(make_article())
