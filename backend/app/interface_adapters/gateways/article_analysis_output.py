from pydantic import BaseModel, ConfigDict

from app.entities.article_analysis import ArticleAnalysis
from app.entities.category import Category


class ArticleAnalysisOutput(BaseModel):
    """Claude APIの構造化出力のスキーマ（項目名はシステムプロンプトの見出しと一致させる）。

    `messages.parse()` の `output_format` に渡し、応答をこの型として検証させる。
    カテゴリは `Category` の値に限定されるため、未知のコードは返らない。
    """

    model_config = ConfigDict(frozen=True)

    summary_text: str
    matched_categories: list[Category]
    mentions_price: bool
    mentions_israel: bool

    def to_entity(self) -> ArticleAnalysis:
        """エンティティに変換する。モデルが同じカテゴリを重複して返しても、順序を保って1つにまとめる。

        Raises:
            ValueError: 要約が空の場合（`ArticleAnalysis` の検証による）。
        """
        return ArticleAnalysis(
            summary_text=self.summary_text.strip(),
            matched_categories=tuple(dict.fromkeys(self.matched_categories)),
            mentions_price=self.mentions_price,
            mentions_israel=self.mentions_israel,
        )
