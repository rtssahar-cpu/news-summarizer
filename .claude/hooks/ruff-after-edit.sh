#!/usr/bin/env bash
# PostToolUse フック: backend/ 配下の Python ファイルを編集した直後に Ruff で自動修正・整形し、
# 自動修正できない違反が残っていれば exit 2 で Claude に返して修正させる。
# Ruff は backend/uv.lock で固定されたバージョンを使う（CI・pre-commit と同じ）。
set -uo pipefail

project_root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
file_path=$(jq -r '.tool_input.file_path // .tool_response.filePath // empty')

if [ -z "$file_path" ]; then
  exit 0
fi
case "$file_path" in
  /*) ;;
  *) file_path="$project_root/$file_path" ;;
esac
case "$file_path" in
  "$project_root"/backend/*.py) ;;
  *) exit 0 ;;
esac

cd "$project_root" || exit 0
ruff() { uv run --project backend --locked --quiet ruff "$@"; }

ruff check --fix --quiet "$file_path" >/dev/null 2>&1
ruff format --quiet "$file_path" >/dev/null 2>&1

if ! remaining=$(ruff check --quiet --output-format concise "$file_path" 2>&1); then
  {
    echo "Ruff の違反が残っています（自動修正できないもの）。修正してください:"
    echo "$remaining"
  } >&2
  exit 2
fi
exit 0
