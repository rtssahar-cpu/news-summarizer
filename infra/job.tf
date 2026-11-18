# 日次処理（記事の取得・分類・要約・保存）。App と同じ環境・イメージを使い、起動コマンドだけ変える
# 設定の方針は docs/BACKEND_PLAN.md の「ACA Jobsのデプロイ方針（ステップ5-10）」参照
resource "azurerm_container_app_job" "daily" {
  name                         = "news-summarizer-daily-job"
  location                     = azurerm_resource_group.main.location
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id

  # 通常は数分で終わる。40記事を順番に処理しても十数分のため、余裕を見て30分で打ち切る
  replica_timeout_in_seconds = 1800
  # 終了コード1はコードや設定の修正が必要な失敗のため、再実行しない
  replica_retry_limit = 0

  schedule_trigger_config {
    # 毎朝 6:00 JST（cron は UTC）
    cron_expression = "0 21 * * *"
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }

  secret {
    name  = "anthropic-api-key"
    value = var.anthropic_api_key
  }

  template {
    container {
      name = "daily-job"
      # 作成時のみ使う値。以降は CI が更新するため ignore_changes で管理から外す
      image   = "ghcr.io/rtssahar-cpu/news-summarizer/backend:ac78df21953400fae9c3ccdd15feb6581ee99f30"
      command = ["python", "-m", "app.frameworks.daily_job"]
      cpu     = 0.5
      memory  = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "ANTHROPIC_API_KEY"
        secret_name = "anthropic-api-key"
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}
