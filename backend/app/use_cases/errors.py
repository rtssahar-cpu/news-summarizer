class ApplicationError(Exception):
    """アプリケーション内で発生する、上位層が扱うべき例外の基底クラス。

    サブクラスは「どこで起きたか」ではなく「誰が何をすべきか」で分類する。
    """


class ExternalServiceError(ApplicationError):
    """外部起因のエラー（ニュースサイトの5xx、LLM APIのタイムアウト等）。

    自分では直せないため、放置またはリトライで対処する。ログレベルはWARNとし、通知の対象にしない。
    """


class InternalError(ApplicationError):
    """自分起因のエラー（パース結果が想定外、DB保存の失敗等）。

    コードの修正が必要なため、ログレベルはERRORとし、通知の対象にする。
    外部サイトのHTML構造変更のように原因が外部でも、対応がコード修正であればこちらに分類する。
    """


class ArticleSourceUnavailableError(ExternalServiceError):
    """記事の取得元（防衛省サイト等）全体から記事を取得できないことを表す。

    個別記事の取得失敗ではなく、一覧ページの取得失敗など、そのソースの処理を継続できない場合に送出する。
    """

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"記事ソース '{source}' から記事を取得できません: {reason}")
        self.source = source
        self.reason = reason


class ArticleContentUnavailableError(ExternalServiceError):
    """個別記事の本文を取得・抽出できないことを表す（PDFが壊れている等）。

    その記事だけの問題であり、呼び出し元は記事をスキップして処理を継続する。
    """


class SourceStructureChangedError(InternalError):
    """記事の取得元のページ構造が想定と異なり、記事情報を抽出できないことを表す。

    原因は取得元サイトの変更だが、対応はパース処理の修正となるため自分起因に分類する。
    """

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"記事ソース '{source}' のページ構造が想定と異なります: {reason}")
        self.source = source
        self.reason = reason
