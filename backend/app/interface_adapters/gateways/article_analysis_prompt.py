from datetime import timedelta, timezone

from app.entities.article import Article
from app.entities.article_analysis import ISRAEL_MENTION_CRITERION, PRICE_MENTION_CRITERION
from app.entities.category import CATEGORY_CRITERIA

JST = timezone(timedelta(hours=9))

# 要約に含める項目（該当しない項目は省略させる）
SUMMARY_ITEMS = ("概要", "関係する企業・組織", "装備品・技術", "金額・数量", "時期・今後の予定")


def build_system_prompt() -> str:
    """記事の分析方法（カテゴリ・フラグの判定基準と要約の形式）を指示するシステムプロンプトを返す。"""
    category_lines = "\n".join(
        f"- {category.value}: {criterion}" for category, criterion in CATEGORY_CRITERIA.items()
    )
    summary_item_lines = "\n".join(f"- {item}" for item in SUMMARY_ITEMS)
    return f"""あなたは日本の防衛・安全保障分野のニュースを分析するアナリストです。
防衛省・防衛関連企業の公式発表等の記事を1件受け取り、要約と分類を行います。

## matched_categories（該当するカテゴリ）
以下の基準を満たすカテゴリのコードをすべて挙げてください（複数該当あり得ます）。
防衛と無関係な記事は空のリストにしてください。
大きさ・航続距離等の数値基準は、記事に数値がなくても機種名等から満たすと判断できれば該当とします。

{category_lines}

## mentions_price
{PRICE_MENTION_CRITERION}場合に true としてください。

## mentions_israel
{ISRAEL_MENTION_CRITERION}場合に true としてください。

## summary_text（要約）
以下の項目ごとに「項目名: 内容」の形で、1項目1行で記載してください。
記事に該当する内容がない項目は行ごと省略してください（「概要」は必ず記載します）。
防衛と無関係な記事も同じ形式で要約してください。

{summary_item_lines}

要約は記事に書かれている事実のみに基づき、推測や記事にない情報を加えないでください。"""


def build_user_message(article: Article) -> str:
    """分析対象の記事を、本文と区別しやすいようタグで囲んだユーザーメッセージを返す。"""
    # DBから読み出した記事はUTCになり得るため、日本時間の日付に揃える
    published_date = article.published_at.astimezone(JST).date().isoformat()
    return f"""以下の記事を分析してください。

<article>
<title>{article.title}</title>
<published_date>{published_date}</published_date>
<url>{article.url}</url>
<body>
{article.body}
</body>
</article>"""
