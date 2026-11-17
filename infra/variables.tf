# シークレットの値はコードに書かず、TF_VAR_* の環境変数で渡す（~/.config/news-summarizer/terraform.env。
# 作成は scripts/create-terraform-env.sh）。sensitive は画面表示を隠すだけで、state には平文で入る

variable "database_url" {
  description = "Neon の接続文字列（App・Job の DATABASE_URL）"
  type        = string
  sensitive   = true
}
