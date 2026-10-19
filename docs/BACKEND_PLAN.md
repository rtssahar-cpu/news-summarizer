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
3. ✅ 8社（三菱重工・川崎重工・スバル・IHI・三菱電機・NEC・富士通・日立）のプレスリリース取得アダプタ（共通ポート `app/use_cases/article_fetcher.py` の `ArticleFetcher` に準拠させる。富士通は取得手段がないため対象外）
   - ✅ 三菱重工（`mhi_fetcher.py`。`feat/phase1-mhi-fetcher`）
   - ✅ 川崎重工（`khi_fetcher.py`。`feat/phase1-khi-fetcher`）
   - ✅ スバル（`subaru_fetcher.py`。`feat/phase1-subaru-fetcher`）
   - ✅ IHI（`ihi_fetcher.py`。`feat/phase1-ihi-fetcher`）
   - ✅ 日立（`hitachi_fetcher.py`。`feat/phase1-hitachi-fetcher`）
   - ✅ 三菱電機（`melco_fetcher.py`。`feat/phase1-melco-fetcher`）
   - ✅ NEC（`nec_fetcher.py`。`feat/phase1-nec-fetcher`）
   - ➖ 富士通（対象外。サイト全体がbot対策でブロックされ、正規の取得経路がないため。下記参照）
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
| スバル | `subaru.co.jp/news/` | ✅実装済み。RSSなし。一覧ページ→記事ページのHTML解析（下記参照） |
| IHI | `ihi.co.jp/all_news/` | ✅実装済み。RSSなし。一覧ページ→記事ページのHTML解析（下記参照） |
| 三菱電機 | `mitsubishielectric.co.jp/ja/pr/` | ✅実装済み。一覧はJSで描画されるため裏で読み込むJSON→記事PDF（下記参照） |
| NEC | `jpn.nec.com/press/` | ✅実装済み。一覧はJSで描画されるため裏で読み込むRSS `/ja/press/press.xml` →記事ページのHTML解析（下記参照） |
| 富士通 | `global.fujitsu/ja-jp/pr` | **対象外。** サイト全体が429（Vercel Security Checkpoint）でブロックされ、正規の取得経路がない（下記参照） |
| 日立 | `hitachi.com/ja-jp/press/` | ✅実装済み。一覧はJSで描画されるため裏で読み込むJSON→記事PDF（下記参照） |

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

#### スバル

- **RSSがないため一覧ページを解析する:** `/news/` の `div.component-newsList li` が1件ずつのニュース（新しい順）。
  一覧に載るのは**その年のニュースのみ**のため、年始は `limit` 件に満たないことがある（毎朝の新着取得には支障ないため、
  前年の一覧はたどっていない）。決算発表の項目はリンク先がIR資料（`/ir/library/results.html`）のため対象外
  （`/news/YYYY_MM_DD_N` 形式のリンクのみ対象）
- **全ニュースを対象にする:** 大半は自動車関連で、防衛関連は「航空宇宙カンパニー」カテゴリ（年1〜2件程度）にほぼ限られるが、
  他カテゴリに分類された防衛関連記事を取りこぼさないよう、カテゴリでは絞らずカテゴリ判定（ステップ4）に任せる
- **発表日は一覧の `<time>2026/10/05</time>` を使う:** 時刻はないため日本時間の0時とする
- **記事ページの本文は `div#text`:** 本文を囲む要素がなく、日付（`div.newsHeader`）・タイトル（`h1`）・PDFボタン
  （`div.newsFooter`）と同じ階層に並ぶため、それらを除いて抽出する。注釈（`*1：...`）は `<div>` で書かれるため `<div>` も
  1行の単位とする。行の抽出処理はKHIと共通（`html_text.py`）
- **PDF版は取得しない:** 記事によっては `[PDF]` ボタンがあるが、HTMLの本文と同じ内容と考えられるため（PDFの中身は未確認）

#### IHI

- **RSSがないため一覧ページを解析する:** `/all_news/` はタブ構成で、種別ごとのタブ（`#tab02`〜）にも同じニュースが
  重複して載るため、「すべて」のタブ（`div#tab01 ul.m-news > li`）だけを見る。一覧に載るのは**今年度（4月〜）のニュースのみ**
- **対象は `/all_news/YYYY/<分野>/NNN_NNN.html` 形式のリンクのみ:** 種別は「プレスリリース」「お知らせ」「適時開示」が混在する。
  適時開示（決算等のPDF）、IR・研究開発のページへのリンク、リンクのない項目は対象外。スバルと同様、分野（航空・宇宙・防衛等）
  では絞らずカテゴリ判定（ステップ4）に任せる
- **発表日は `<time>` の表示テキスト（`2026年10月07日`）を使う:** `datetime` 属性は重複側のタブで全件 `2022-10-19` に
  なっているなど信用できないため。時刻はないため日本時間の0時とする
- **記事ページの本文は `div.m-entry-detail`:** ヘッダー（日付・種別・タイトル）、English pageへのリンク（`p.m-en-link`）、
  「ニューストップへ」（`p.m-entry-detail_back`）を除いて抽出する。副題（`h1 > div.size-xsmall`）は一覧のタイトルに含まれない
  ため本文の先頭に加える。小見出し（`<h4>`）・特長の一覧（`<dt>`/`<dd>`）も1行の単位とする

#### 日立

- **一覧は裏で読み込むJSONを直接取得する:** `/ja-jp/press/` の一覧はJSで描画されるため、
  `/content/hitachi/global/ja_jp/press/jcr:content/root/main-container/initial-container/page_search_copy_cop.json`
  を取得する（新しい順に12件。`?page=2` で次の12件も取れるが、`limit` に足りるため使っていない）。
  対象は `newsPath` が `/ja-jp/press/articles/YYYY/MM/MMDD[a-z]/` 形式の項目のみ（2026-10-18時点で直近180件はすべてこの形式）。
  スバル・IHIと同様、カテゴリ（`displayTags`）では絞らずカテゴリ判定（ステップ4）に任せる
- **発表日は `publishDateValue`（`2026-10-16T17:00:00`）を使う:** タイムゾーンはないため日本時間とする。時刻まで取れる
- **本文はPDFから取得する:** 記事ページの大半（12件中10件）は日付・タイトル・「PDFをダウンロード」ボタンのみで、本文がHTMLにない。
  全記事にPDFがあるため、HTMLの本文の有無にかかわらず常にPDFを使う
- **PDFのURLは記事URLから導いている:** `/ja-jp/press/articles/2026/10/1016a/` →
  `/content/dam/hitachi/global/ja_jp/press/files/2026/10/1016a.pdf`（過去分21件で、記事ページ内のリンクと一致することを確認）。
  記事ページは取得しない
- **PDFはAESで暗号化されている:** 閲覧用パスワードはないが権限制限付きで、pypdfでの復号に `cryptography` が必要（依存に追加済み）。
  なお、ライブラリ不足時にpypdfが送出する `DependencyError` は `PyPdfError` を継承していないため、`pdf_text.py` で個別に捕捉している
- **`Article.url` は記事ページのURLにする:** 人が読むページを保存し、PDFのURLは本文の取得にのみ使う。
  抽出した本文にはページ番号（`1/2`）や `Press Release` も含まれるが、要約への影響は小さいため除去していない

#### 三菱電機

- **一覧は裏で読み込むJSONを直接取得する:** `/ja/pr/` の一覧はJSで描画されるため、
  `/global/common/mel25/news-data/jws-news/japan/www/ja/news-article.json` を取得する（2023年1月以降の全件、約700件。新しい順）。
  一覧ページの `data-js-newsjsonpath` 属性にある `/content/dam/prod/...` で始まるパスは404で、`data-js-prod-newsjsonpath` の方が正しい
- **対象は三菱電機本体の発表のみ:** リンク先は記事ページ（`/ja/pr/YYYY/<ID>/`）、PDFのみの発表（`/ja/pr/YYYY/pdf/<ID>.pdf`）、
  子会社等の他サイト（三菱電機ビルソリューションズ・三菱電機モビリティ等。`linkType` が `external`、または他ドメインのPDF）の3種類。
  子会社の発表は防衛関連をほぼ含まないため対象外とした。他社と同様、カテゴリ（`categories`。`防衛・宇宙システム` 等）では絞らない
- **発表日は `articlePublishtime`（`2026-10-16T19:30:00+09:00`）を使う:** タイムゾーン付きで時刻まで取れる
- **本文はPDFから取得する:** 記事ページにも同じ内容の「リリース全文」PDFがあり、URLは記事URLから導ける
  （`/ja/pr/2026/1013_co/` → `/ja/pr/2026/pdf/1013_co.pdf`）。PDFのみの発表はリンク先のPDFをそのまま使う
- **「リリース全文」PDFがない記事は、分割されたPDFをすべて連結する:** 決算・IR Day・子会社化等の記事（直近約150件中8件）は
  記事ページに本文がなく、分割されたPDF（`0820_ei1.pdf`〜、`0909-1.pdf`〜）へのリンクのみが並ぶ。導いたPDFが404の場合のみ
  記事ページを取得し、同じ記事のPDFをすべて取得して連結する（`melco_article_parser.py`）。IR Dayの事業別資料等に防衛関連の
  内容が含まれ得るため、先頭のPDFだけでなく全PDFを使う（本文は数十ページに及ぶことがある）。分割PDFのうち1つでも取得・抽出に
  失敗した場合は記事ごとスキップする
- **PDFの存在確認にHEADを使わない:** HEADリクエストでは404を返すが、GETでは取得できるPDFがある（`0304.pdf` 等）
- **`Article.url` は記事ページのURLにする:** 日立と同様。PDFのみの発表はPDFのURLになる

#### NEC

- **一覧は裏で読み込むRSSを直接取得する:** `/press/` の一覧はJSで描画されるため、`press_common.js` が読み込んでいる
  RSS `/ja/press/press.xml`（新しい順に約100件）を取得する。一覧ページで読み込まれるCSV（`/corporateblog/csv/data.csv`）は
  コーポレートブログ（NEC Stories）用で、プレスリリースではない
- **対象はNEC本体の発表のみ:** RSSには子会社（NECネクサソリューションズ・NEC通信システム等。他ドメイン）の発表も含まれるが、
  三菱電機と同様に対象外とした（`https://jpn.nec.com/press/YYYYMM/YYYYMMDD_NN.html` 形式のリンクのみ対象）。
  他社と同様、カテゴリ（`<category>`）では絞らない
- **発表日は `pubDate` を使う:** 防衛省と異なり、実際の発表日時（`10:00`・`15:30` 等）になっている
- **記事ページの本文は `div.str-column-main`:** SNSの共有ボタン（`div.comp-sns`）と末尾の定型文（`div.mod-box`）を除いて
  抽出する。副題（`div.str-pageTitle span.sub`）は本文の領域の外にあり、RSSのタイトルにも含まれないため本文の先頭に加える。
  「以上」の後の注記（`(注1)`〜）は「防衛装備庁が実施する…」のような補足を含むことがあるため、お問い合わせ先とともに残している
- **添付PDFは取得しない:** 一部の記事にあるPDF（受賞者の略歴等）は補足資料のため。社債発行の告知のように本文がPDFにしかない
  記事もあるが（本文はタイトル程度になる）、財務関連で防衛関連の内容は含まないため対応していない

#### 富士通（対象外）

2026-10-19時点で、正規の経路で本文を自動取得する手段が見つからなかったため、取得アダプタは実装していない。

- **`global.fujitsu` はドメイン全体がブロックされる:** 一覧・記事ページ・`robots.txt`・`favicon.ico` まで、すべて429
  （Vercel Security Checkpoint。ブラウザでJSを実行させて人間かを確かめる仕組み）。本番環境（Azure）からも同様と考えられる。
  ヘッドレスブラウザ等でチャレンジを突破することは、サイトのbot対策の回避にあたるため行わない
- **旧URLは使えない:** `pr.fujitsu.com/jp/news/`（旧RSS含む）は `info.archives.global.fujitsu` へ転送されるが404
- **Googleニュースの検索RSSは見出しのみ:** `news.google.com/rss/search?q=site:global.fujitsu/ja-jp/pr` は取得できるが、
  本文がなくリンク先もブロックされる `global.fujitsu` のため、要約に使えない
- **日経プレスリリースは使わない:** 一覧がJSで描画されるうえ、日経は自動収集・機械学習での利用を個別の問い合わせ扱いとしている
- **富士通の防衛関連の動きは他ソースで補う:** 防衛省の発表、フェーズ2・3（日経・専門メディア）の記事で
  `contractor_fujitsu` カテゴリに分類されることを想定する（カテゴリ自体は残す）。富士通がRSS等を提供した場合は再調査する

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
