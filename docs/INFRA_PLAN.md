# インフラ 実装計画・運用ルール

news-summarizerのAzureリソースをTerraformで管理するためのルールと、作業の進捗をまとめたもの。
`infra/` に触れる前、またはAzureのリソースを追加・変更する前には必ず目を通すこと。
アプリ側の要件（Jobの実行時刻など）は `docs/BACKEND_PLAN.md` を参照する。

## 方針

2026-10-29にユーザーと合意した方針。

- **インフラはTerraformで管理する（IaC）:** 今後リソースを追加する場合も、なるべくTerraformで書く。
  Portalや `az` での手動作成は、下記のstate用ストレージアカウントのように、Terraformで作れないものに限る
- **既存のリソース（リソースグループ・Container Apps環境・Container App等）も管理する:** いずれも手動で作成済みのため、
  Terraform 1.5以降の `import` ブロックで取り込む

## 実装のルール

- コードは `infra/` に置く
- Terraformのバージョンは `required_version`、providerのバージョンは `.terraform.lock.hcl` で固定する（lockファイルはコミットする）
- App・Jobのイメージは `deploy-backend.yml` が更新するため、`lifecycle { ignore_changes }` でTerraformの管理から外す
  （外さないと、`plan` のたびにイメージを古いタグへ戻そうとする）
- シークレットの値はコードや `*.tfvars` に書かず、コミットしない。sensitiveな変数（`variables.tf`）にして、値は
  `TF_VAR_*` の環境変数で渡す（2026-11-08にユーザーと合意）
  - 値はdev-vmのリポジトリ外のファイル `~/.config/news-summarizer/terraform.env`（権限600）に置き、`plan`・`apply` の前に
    `source` で読み込む。作成は `infra/scripts/create-terraform-env.sh`（`database_url` は既存のAppのシークレットから取得し、
    `anthropic_api_key` は入力させる。値は画面に表示しない）
  - Container Appsのシークレットは App・Job ごとに登録する必要がある（共有できない）が、コード上は同じ変数を参照する
- **構成図（`docs/architecture.drawio`）も合わせて更新する:** リソースの追加・削除や、通信経路・認証方法などネットワーク構成に
  関わる変更をする場合は、同じPRで構成図も更新する（2026-11-18にユーザーと合意）
  - 破線は「予定・未作成」、実線は「稼働中」を表す。予定のリソースを作成したら実線に変える

## 運用のルール

- **stateはAzure Storageに置く:** stateにはシークレットの値が平文で含まれるため、ローカルやリポジトリには置かない。
  state用のストレージアカウントはTerraform自身では作れないため、手動（Portalまたは `az`）で作成する
- **`terraform apply` はユーザーの確認後に、ユーザーのPCから手動で実行する。** CIからの実行は現時点では行わない
- **importや変更の前に `terraform plan` で差分を確認する:** importの際は、差分が0件になるまでコードを合わせてからapplyする
  （既存の設定を意図せず変えないため）
- **dev-vmでは、VMのマネージドID（システム割り当て）で認証する:** ユーザーのアカウントでの `az login` は、デバイスコード方式が
  Entra IDの「セキュリティの既定値群」にブロックされる（`AADSTS530035`）。代わりに `az login --identity` でログインし、
  Terraformは環境変数 `ARM_USE_MSI=true` を設定して実行する（認証方法はコードに書かない）
  - 権限は `news-summarizer-rg` の共同作成者のみ（2026-11-03にサブスクリプション全体から絞った）。dev-vm上のどのプロセスも
    この権限を使えるため、広げる場合は必要な範囲に限る。ロールの割り当て（`azurerm_role_assignment`）は作成できない
  - サブスクリプションIDは、別のサブスクリプションへ誤って適用しないよう `versions.tf`（backend）と `providers.tf` に明示している

## 進捗（ACA Jobsのデプロイ。`docs/BACKEND_PLAN.md` のステップ5-10）

1. ✅ Terraformの導入（HashiCorpの公式aptリポジトリ。v1.17.1）・ログイン（マネージドID。上記「運用のルール」参照）
2. ✅ state用のストレージアカウントの作成（2026-11-03、ユーザーがPortalで作成）
   - ストレージアカウント `stnewssumtfstate`（リソースグループ `news-summarizer-rg`）・コンテナ `tfstate`（プライベート）
   - Standard・LRS・BLOBの匿名アクセスはオフ・最小TLS 1.2・BLOBのバージョン管理はオン・論理的な削除は7日
   - ストレージアカウントキーのアクセスはオン（Entra ID認証に切り替える場合は、自分に「ストレージ BLOB データ共同作成者」が必要）
3. ✅ `infra/` の土台（`versions.tf`・`providers.tf`・`.gitignore`・`.terraform.lock.hcl`。azurerm 5.12.0。`chore/terraform-setup`）
   - 確認手順: `cd infra && ARM_USE_MSI=true terraform init && terraform fmt -check && terraform validate && terraform plan`
4. ✅ 既存リソースのimport（`plan` の差分0件を確認してからapply）。対象は `news-summarizer-rg`・Log Analytics
   `news-summarizer-env-logs`・Container Apps環境 `news-summarizer-env`・Container App `news-summarizer-backend`
   - ✅ リソースグループ・Log Analytics・環境（2026-11-17にapply済み）
   - ✅ Container App（2026-11-17にapply済み）
   - コードは `plan -generate-config-out` で生成し、既定値と同じ項目を省いて整理した（生成されるコードにシークレットの値は
     含まれない）。`import` ブロック（`imports.tf`）はapply後も残してよい（取り込み済みなら何もしない）
5. ⬜ Jobの追加
6. ⬜ `deploy-backend.yml` に `az containerapp job update --image` を追加（OIDCのサービスプリンシパルにJobを更新する
   権限があるかも確認する）
7. ⬜ 本番での初回の手動実行（`az containerapp job start`）・ログとNeonへの保存の確認・ドキュメントの更新
   （`.env.example` に `ANTHROPIC_API_KEY` の欄を追加することも含む）
