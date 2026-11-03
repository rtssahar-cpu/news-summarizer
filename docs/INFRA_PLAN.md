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
- シークレットの値はコードや `*.tfvars` に書かず、コミットしない

## 運用のルール

- **stateはAzure Storageに置く:** stateにはシークレットの値が平文で含まれるため、ローカルやリポジトリには置かない。
  state用のストレージアカウントはTerraform自身では作れないため、手動（Portalまたは `az`）で作成する
- **`terraform apply` はユーザーの確認後に、ユーザーのPCから手動で実行する。** CIからの実行は現時点では行わない
- **importや変更の前に `terraform plan` で差分を確認する:** importの際は、差分が0件になるまでコードを合わせてからapplyする
  （既存の設定を意図せず変えないため）
- `az login` の際はテナントを指定する（ユーザーのアカウントは既定のテナントにサブスクリプションがないため）:
  `az login --use-device-code --tenant <テナントID>`。テナントIDはPortalの「Microsoft Entra ID」→「概要」、
  またはGitHubのシークレット `AZURE_TENANT_ID` の値

## 進捗（ACA Jobsのデプロイ。`docs/BACKEND_PLAN.md` のステップ5-10）

1. 🔄 Terraformの導入（HashiCorpの公式aptリポジトリ。v1.17.1を導入済み）・`az login`（Claude Codeのセッションからは
   未ログインのため、要確認）
2. ✅ state用のストレージアカウントの作成（2026-11-03、ユーザーがPortalで作成）
   - ストレージアカウント `stnewssumtfstate`（リソースグループ `news-summarizer-rg`）・コンテナ `tfstate`（プライベート）
   - Standard・LRS・BLOBの匿名アクセスはオフ・最小TLS 1.2・BLOBのバージョン管理はオン・論理的な削除は7日
   - ストレージアカウントキーのアクセスはオン（Entra ID認証に切り替える場合は、自分に「ストレージ BLOB データ共同作成者」が必要）
3. ⬜ `infra/` の土台（provider・backend・バージョンの固定・`.gitignore`）。azurermは5.x（2026-11-03時点の最新は5.12.0）
4. ⬜ 既存リソースのimport（`plan` の差分0件を確認してからapply）
5. ⬜ Jobの追加
6. ⬜ `deploy-backend.yml` に `az containerapp job update --image` を追加（OIDCのサービスプリンシパルにJobを更新する
   権限があるかも確認する）
7. ⬜ 本番での初回の手動実行（`az containerapp job start`）・ログとNeonへの保存の確認・ドキュメントの更新
   （`.env.example` に `ANTHROPIC_API_KEY` の欄を追加することも含む）
