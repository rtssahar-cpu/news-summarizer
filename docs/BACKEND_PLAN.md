# バックエンド 実装計画・アーキテクチャ

news-summarizerバックエンドの現状のアーキテクチャルールと、実装ロードマップ・進捗状況をまとめたもの。
バックエンドのコードに取り組む前には必ず目を通すこと。フロントエンド側の計画は別途`docs/FRONTEND_PLAN.md`
（未作成）を参照する想定。

## 構成

- `backend/`: FastAPI + SQLAlchemy + Alembic（Python 3.12、uv で依存管理）
- ローカル開発は `docker compose up`（db / backend / frontend）

## レイヤー構成（import-linter で CI が強制）

- `app/frameworks` → `app/interface_adapters` → `app/use_cases` → `app/entities` の一方向のみ import 可
- `entities` / `use_cases` から fastapi / starlette / sqlalchemy / alembic / psycopg / uvicorn の import は禁止
- 環境変数などの外部入力は `frameworks` 層で読み、引数で内側に注入する（例: `create_app(app_version)`）

## 完了の条件（コードを変更したら必ず実行し、すべて通すこと）

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run mypy            # strict
uv run lint-imports    # レイヤー違反の検出
uv run pytest --cov    # カバレッジ 80% 未満は失敗
```

- CI と同じ条件で確認する場合: `docker build --target test backend`
- Ruff のルール（複雑度・セキュリティ等）は `backend/pyproject.toml` を参照。`# noqa` での回避は最終手段とし、理由をコメントに書く
- Ruff のバージョンは `backend/uv.lock` で一元管理（pre-commit も uv 経由で同じ Ruff を使う）

## CI/CD（`.github/workflows/`）

- `backend-ci.yml`: 毎回起動し、変更がなければジョブをスキップする。**ジョブの `name` は Ruleset の必須チェック名と一致させているため変更しない**
- main への push で backend が変わっていれば、テスト・スモークテスト成功後に `deploy-backend.yml` が呼ばれ、ghcr.io にイメージを push した上で Azure Container Apps へデプロイされる（OIDC認証、シークレット不要）
- デプロイ後に本番の `/health` の `version` がコミット SHA と一致するか確認する
- インフラ（Container App の作成・シークレット・レプリカ数）は CI の管理外。ワークフローではイメージ更新のみ行う

## 外部サービス

- DB: Neon（サーバーレスPostgres。自動サスペンドでアイドル時ほぼ無料）
- バックエンドホスティング: Azure Container Apps（スケールtoゼロ）
- フロントエンドホスティング: Azure Static Web Apps（予定、未着手）

## 全体ロードマップ

- A. アプリ本体の機能実装（進行中。下記「機能ロードマップ」参照）
- B. DBの本番ホスティング（Neon）— ✅完了
- C. フロントエンド⇔バックエンドの疎通設計（CORS等）— ⬜未着手
- D. CI/CD — ✅完了（バックエンドのみ。フロントエンドのAzure Static Web Appsへのデプロイ設定は未着手）
- E. 認証・アクセス制御 — ⬜未着手（本格運用前に最低限のアクセス制限を検討すること）

## 機能ロードマップ（A: アプリ本体）

想定利用: 毎朝、特定ジャンルのニュース記事をAIで要約する防衛関連ニュースアプリ。想定利用者は1〜2人（家庭用）。

- フェーズ1: 防衛省＋防衛装備8社の公式発表（**今ここ**）
- フェーズ2: 日経新聞
- フェーズ3: 専門メディア（朝雲新聞、海外メディア等）

### フェーズ1のステップ

1. ✅ DBスキーマ設計（`Article`/`Summary`エンティティ、ORMモデル。`feat/phase1-db-schema`でマージ済み）
2. ✅ 防衛省の取得アダプタ（`app/interface_adapters/gateways/mod_fetcher.py`。`feat/phase1-mod-fetcher`、RSS経由への切り替えは`fix/mod-fetcher-use-rss`）
3. 🔄 8社（三菱重工・川崎重工・スバル・IHI・三菱電機・NEC・富士通・日立）のプレスリリース取得アダプタ（共通ポート `app/use_cases/article_fetcher.py` の `ArticleFetcher` に準拠させる。富士通は後回し）
   - ✅ 三菱重工（`mhi_fetcher.py`。`feat/phase1-mhi-fetcher`）
   - ✅ 川崎重工（`khi_fetcher.py`。`feat/phase1-khi-fetcher`）
   - ⬜ スバル・IHI・三菱電機・NEC・日立・富士通
4. ⬜ カテゴリ判定＋要約ユースケース（Claude APIを使用。`app/entities/category.py`の分類に基づく）
5. ⬜ 日次処理ユースケース（各ソースから5件程度取得→本文取得→分類・要約→DB保存、を束ねる）
6. ⬜ APIエンドポイント（フロントエンド向けに、その日の要約一覧を返す）

### データソースに関する注意点（防衛省）

防衛省サイト（mod.go.jp）はトップページ・個別記事ページ・月別/年別の一覧・RSS案内ページがCloudflareの自動化対策で
ブロックされる。**ブロックされないのは「RSS本体」（`/j/rss/news.xml`）と「PDF版（印刷用）」のみ**であるため、
RSSでお知らせ一覧を取得→PDFテキスト抽出、という経路で実装している（`mod_rss_parser.py` / `mod_fetcher.py`）。
8社のサイトを追加する際も、同様にCloudflare等のbot対策の有無を個別に確認すること。

- **PDFのURLは推測している:** RSSにはPDFへのリンクも本文も含まれないため、記事URL `/j/press/news/YYYY/MM/DDx.html`
  の拡張子を `.pdf` に置き換えて取得する（RSSのリンクが最初からPDFの場合はそのまま使う）。PDF版がないお知らせも多く
  （2026年10月分で約半数が404）、取得できない記事はスキップし、`limit` 件そろうまで最大 `limit × 3` 件試す
- **対象は `/j/press/news/` 配下のお知らせのみ:** RSSには `/j/approach/` 等のページ（会談の結果概要など）も含まれるが、
  ブロックされ本文を取得できないため対象外としている
- **発表日はURLの日付を使う:** RSSの `pubDate` は実際の発表日時ではなくRSSの更新時刻（同じ時刻のお知らせがまとめて並ぶ）
  であるため

#### 解決済み: お知らせ一覧ページが古い内容のまま（2026-10-18）

当初は「お知らせ一覧ページ」（`/j/press/news/index.html`、ブロックされない）を解析していたが、最新のお知らせが9/30で
止まっていた。キャッシュを避けるクエリ付きURLで取得しても（`cf-cache-status: MISS`）`last-modified` は10/8のままだった
ため、Cloudflareのキャッシュではなく**防衛省側でページが更新されていない**と判断し、上記のRSS経由に切り替えた。

### データソースに関する注意点（防衛産業8社）

2026-10-18時点で、各社のプレスリリース一覧ページへのアクセスを確認した結果（実装済みの会社以外は、個別記事ページは未確認）。

| 会社 | 一覧ページ | 状況・取得方法の候補 |
|---|---|---|
| 三菱重工 | `mhi.com/jp/news/` | ✅実装済み。RSS `/jp/rss/mhi_news.xml` →記事ページのHTML解析（Cloudflare経由だが通る） |
| 川崎重工 | `khi.co.jp/pressrelease/` | ✅実装済み。RSS `/pressrelease/rss/pressrelease.xml` →記事ページのHTML解析 or PDF（下記参照） |
| スバル | `subaru.co.jp/news/` | 取得可（`/press/` は404）。記事URLに日付を含む |
| IHI | `ihi.co.jp/all_news/` | 取得可。HTML解析 |
| 三菱電機 | `mitsubishielectric.co.jp/ja/pr/` | 取得可だが一覧はJSで描画。裏で読み込むデータの調査が必要 |
| NEC | `jpn.nec.com/press/` | 取得可だが一覧はJSで描画（CSVを読み込んでいる）。CSVの直接取得を検討 |
| 富士通 | `global.fujitsu/ja-jp/pr` | **429（Vercel Security Checkpointでブロック）**。別経路を調査する（後回し） |
| 日立 | `hitachi.com/ja-jp/press/` | 取得可。HTML解析 |

#### 川崎重工

- **RSSのリンク先が3種類ある:** 記事ページ（`/pressrelease/detail/YYYYMMDD_N.html`）、PDFのみの発表
  （`/pressrelease/news_YYMMDD-N.pdf`。人事異動・他社との共同発表等）、IR資料（`/ir/library/` 等）が混在する。
  URLが `.pdf` なら `extract_pdf_text`、それ以外は記事ページとして本文を抽出する。IR資料はページ構造が異なり、
  装備品に関する情報もほぼないため対象外としている（`/pressrelease/` 配下以外はスキップ）
- **記事ページの本文は `div.news-detail-area`:** 副題（`div.heading_subtitle`）はRSSのタイトルに含まれないため本文の先頭に
  加える。本文は `<span>2026</span>年` のように1文の中が細かくタグで区切られているため、`<p>`/`<td>`/`<li>` を1行の単位とし、
  `<br>` の位置だけで改行する（`get_text("\n")` だと文の途中で改行される）
- **発表日は `pubDate` を使う:** 防衛省と異なり、実際の発表日時になっている。`Wed,14 Oct` のようにカンマの後に空白が
  ない形式も混ざるが、`parsedate_to_datetime` で解析できる
- **画像だけのPDFはスキップする:** テキストを抽出できず空になるため、`ArticleContentUnavailableError` として扱う

### カテゴリ分類（`app/entities/category.py`）

記事ごとに、以下のいずれに該当するかをAIで判定する（複数該当あり得る）。

- 日本の装備品に関する新しい動き
- 防衛産業8社の動き（三菱重工／川崎重工／スバル／IHI／三菱電機／NEC／富士通／日立。それぞれ個別カテゴリ。海外企業との連携に特に関心）
- 無人アセット関連（UUV 10m以上／USV／UGV／UAV 1t以上／徘徊型無人機 600km以上）
- 防空システム
- AMD・IAMD
- スタンドオフミサイル（陸海空）
- 電子戦
- 早期警戒機
- 防衛大臣・小野寺大臣の動き（装備品関連のみ）
- 国家安全保障戦略等の3文書に関する動き

上記に加え、`Summary`には横断的なフラグとして `mentions_price`（装備品の価格言及）・`mentions_israel`（イスラエル関連）
を持たせている。

### 非公開情報についての方針（重要・変更しないこと）

「非公開情報」の収集は、**公開されてはいるが見つけにくい情報（業界専門紙・調達公示・IR資料等）に限る**。
本来機密指定・非公開とされている情報の収集は対象外であり、今後も一貫してこの方針を変更しない。

## エラーハンドリング方針

低レベルな処理（HTTP通信、PDF解析等）の例外（`httpx.HTTPError`等）を、呼び出し元の層が理解できる意味のある例外
（ドメイン/ユースケースレベルのエラー）に変換してから上位に伝搬させる、段階的な変換（レイヤーごとの「ピラミッド」構造）
を採用する。下位層の実装詳細を上位層に漏らさないことで、原因追及のしやすさとレイヤー間の疎結合を両立する。

### 例外の一元管理（`app/use_cases/errors.py`）

アプリ独自の例外は**すべてこのファイルに定義する**（各gateway等のファイル内に例外クラスを定義しない）。
名前には `pypdf` や特定ソース（防衛省等）のような外側の層の詳細を含めず、「何が起きたか」を表す汎用的な名前にする。
どのソースで起きたかは `source` 等の属性で持たせる。

```
ApplicationError（基底）
 ├── ExternalServiceError（外部起因 → WARN。放置 or リトライ。通知しない）
 │     ├── ArticleSourceUnavailableError   ソース全体から取得できない（一覧ページの取得失敗等）
 │     └── ArticleContentUnavailableError  個別記事の本文を取得・抽出できない（PDFの破損等）
 └── InternalError（自分起因 → ERROR。コードを直す。通知する）
       └── SourceStructureChangedError     取得元のページ構造が想定と異なる
```

### 分類の基準

- **「どこで起きたか」ではなく「誰が何をすべきか」で分類する。** 例: 取得元サイトのHTML構造変更は原因こそ外部だが、
  対応はパース処理の修正なので `InternalError` 側に置く
- 中間の分類（`ConfigurationError` 等）や、リトライ可否を表す属性は、必要になった時点で追加する（先回りして作らない）
- `TypeError` 等の想定外の例外は独自例外にしない。最上位（日次処理の入口等）で「`ExternalServiceError` はWARN、
  それ以外はすべてERROR」として扱う想定

### 各層での扱い

- **gateway**: ライブラリの例外（`httpx.HTTPError`、`pypdf.errors.PyPdfError`等）を捕捉し、`raise ... from error` で
  上記の例外に変換する（元の例外を `__cause__` として残す）
- **個別記事の失敗**（`ArticleContentUnavailableError`、PDF取得の通信エラー）: 警告ログを出してその記事だけスキップし、
  処理を継続する
- **ソース単位の失敗**（`ArticleSourceUnavailableError`、`SourceStructureChangedError`）: 握りつぶさず上位へ伝搬させる
- **APIのエラーレスポンス**: FastAPIの例外ハンドラーで `ApplicationError` をHTTPレスポンスに変換する。
  APIエンドポイント（フェーズ1のステップ6）の実装時に合わせて行う（未着手）
