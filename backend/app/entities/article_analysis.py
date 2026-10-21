from dataclasses import dataclass

from app.entities.category import Category

# AIに渡す横断的なフラグの判定基準
PRICE_MENTION_CRITERION = "装備品の価格（単価・契約額・予算額等）に言及している"
ISRAEL_MENTION_CRITERION = "イスラエル（政府・軍・企業・装備品等）に関連する話題を含む"


@dataclass(frozen=True)
class ArticleAnalysis:
    """1記事をAIで分析した結果（要約・該当カテゴリ・横断的なフラグ）。

    分析時点では記事が未保存で `Article.id` がないため `article_id` を持たず、
    DB保存時に `Summary` へ変換する。
    """

    summary_text: str
    matched_categories: tuple[Category, ...]
    mentions_price: bool
    mentions_israel: bool

    def __post_init__(self) -> None:
        if not self.summary_text.strip():
            raise ValueError("summary_text must not be blank")
        if len(set(self.matched_categories)) != len(self.matched_categories):
            raise ValueError("matched_categories must not contain duplicates")

    @property
    def is_defense_related(self) -> bool:
        """いずれかのカテゴリに該当するか（フロントエンド向けの一覧に載せる対象か）。"""
        return len(self.matched_categories) > 0
