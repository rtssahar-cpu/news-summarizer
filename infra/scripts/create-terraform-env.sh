#!/usr/bin/env bash
# Terraform に渡すシークレットのファイルを、リポジトリの外に権限 600 で作成する（値は画面に表示しない）
# 使い方: az login --identity の後に bash infra/scripts/create-terraform-env.sh
set -euo pipefail
umask 077

env_file="$HOME/.config/news-summarizer/terraform.env"
if [ -e "$env_file" ]; then
  echo "すでに存在するため、上書きせずに終了します: $env_file" >&2
  exit 1
fi

# 既存の App に登録済みの値をそのまま使う（打ち間違いで plan に差分が出ないようにする）
database_url=$(az containerapp secret show \
  --resource-group news-summarizer-rg \
  --name news-summarizer-backend \
  --secret-name database-url \
  --query value -o tsv)
if [ -z "$database_url" ]; then
  echo "App の database-url を取得できませんでした" >&2
  exit 1
fi

read -rsp "ANTHROPIC_API_KEY を入力してください（画面には表示されません）: " anthropic_api_key
echo
if [ -z "$anthropic_api_key" ]; then
  echo "ANTHROPIC_API_KEY が空のため、ファイルを作成せずに終了します" >&2
  exit 1
fi

mkdir -p "$(dirname "$env_file")"
{
  printf 'export TF_VAR_database_url=%q\n' "$database_url"
  printf 'export TF_VAR_anthropic_api_key=%q\n' "$anthropic_api_key"
} > "$env_file"

echo "作成しました: $env_file"
ls -l "$env_file"
