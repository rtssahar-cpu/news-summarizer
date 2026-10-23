import logging

from anthropic import (
    Anthropic,
    APIConnectionError,
    APIStatusError,
    InternalServerError,
    OverloadedError,
    RateLimitError,
    transform_schema,
)
from anthropic.types import Message, OutputConfigParam

from app.entities.article import Article
from app.entities.article_analysis import ArticleAnalysis
from app.interface_adapters.gateways.article_analysis_output import ArticleAnalysisOutput
from app.interface_adapters.gateways.article_analysis_prompt import (
    build_system_prompt,
    build_user_message,
)
from app.use_cases.errors import (
    ArticleAnalysisRequestError,
    ArticleAnalysisUnavailableError,
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5-5"
MAX_OUTPUT_TOKENS = 16_000
# 切り詰めずにスキップする本文の上限（1記事あたりの料金の上限を抑えるため）
MAX_BODY_LENGTH = 200_000
OUTPUT_CONFIG: OutputConfigParam = {
    "effort": "medium",
    "format": {"type": "json_schema", "schema": transform_schema(ArticleAnalysisOutput)},
}


class ClaudeArticleAnalyzer:
    """Claude APIで記事を分析する `ArticleAnalyzer` の実装。"""

    def __init__(self, client: Anthropic) -> None:
        self._client = client

    def analyze(self, article: Article) -> ArticleAnalysis:
        if len(article.body) > MAX_BODY_LENGTH:
            raise ArticleAnalysisUnavailableError(
                article.url,
                f"本文が長すぎます（{len(article.body)}文字。上限{MAX_BODY_LENGTH}文字）",
            )
        try:
            response = self._client.messages.create(
                model=MODEL,
                max_tokens=MAX_OUTPUT_TOKENS,
                system=build_system_prompt(),
                messages=[{"role": "user", "content": build_user_message(article)}],
                output_config=OUTPUT_CONFIG,
            )
        except APIConnectionError as error:
            # タイムアウト（APITimeoutError）も含む。SDKの自動リトライ後もなお失敗した場合に届く
            raise ArticleAnalysisUnavailableError(article.url, f"通信エラー: {error}") from error
        except (RateLimitError, OverloadedError, InternalServerError) as error:
            # 429・529・その他の5xx（SDKは529をInternalServerErrorではなくOverloadedErrorにする）
            raise ArticleAnalysisUnavailableError(
                article.url, f"APIが一時的に利用できません: {error.message}"
            ) from error
        except APIStatusError as error:
            # 認証エラー・400等。どの記事でも同じく失敗するため、設定やコードの修正が必要
            raise ArticleAnalysisRequestError(error.message) from error
        logger.info(
            "記事を分析しました: %s（入力%dトークン、出力%dトークン）",
            article.url,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return _to_analysis(article.url, response)


def _to_analysis(article_url: str, response: Message) -> ArticleAnalysis:
    """応答の停止理由を確認してから、テキストをスキーマで検証してエンティティに変換する。

    `messages.parse()` は停止理由を確認する前にJSONを検証し、拒否や出力上限の場合に原因の分からない
    `ValidationError` になるため、`messages.create()` の応答をここで検証している。
    """
    if response.stop_reason == "refusal":
        raise ArticleAnalysisUnavailableError(article_url, "応答が拒否されました")
    if response.stop_reason == "max_tokens":
        raise ArticleAnalysisUnavailableError(article_url, "応答が出力上限に達しました")
    text = "".join(block.text for block in response.content if block.type == "text")
    # pydanticのValidationErrorもValueErrorのサブクラスのため、まとめて捕捉する
    try:
        return ArticleAnalysisOutput.model_validate_json(text).to_entity()
    except ValueError as error:
        raise ArticleAnalysisUnavailableError(
            article_url, f"応答を解析できません: {error}"
        ) from error
