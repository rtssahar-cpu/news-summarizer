from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta, timezone

from app.use_cases.article_summary_reader import ArticleSummaryReader, SummarizedArticle

# 「その日」は日本時間で区切る（毎朝6:00 JSTに日次処理が動くため）
JST = timezone(timedelta(hours=9))


def current_utc_time() -> datetime:
    return datetime.now(UTC)


class SummarizedArticleLister:
    """指定した日（JST）に要約した記事の一覧を返すユースケース。

    現在時刻の取得（`clock`）は、テストで固定できるよう注入する。
    `clock` はタイムゾーン付きの日時を返すこと。
    """

    def __init__(
        self,
        reader: ArticleSummaryReader,
        clock: Callable[[], datetime] = current_utc_time,
    ) -> None:
        self._reader = reader
        self._clock = clock

    def list_for(self, day: date | None = None) -> tuple[SummarizedArticle, ...]:
        """`day`（JST）の0時から翌日0時までに要約した記事を、発表日の新しい順に返す。

        `day` を省略した場合は今日（JST）とする。該当する記事がなければ空のタプルを返す。

        Raises:
            ArticleStorageError: 保存先にアクセスできない場合（捕捉せずに呼び出し元へ伝える）。
        """
        target_day = day if day is not None else self.today()
        start = datetime.combine(target_day, time.min, tzinfo=JST)
        return self._reader.list_summarized_between(start, start + timedelta(days=1))

    def today(self) -> date:
        """現在の日本時間の日付を返す。"""
        return self._clock().astimezone(JST).date()
