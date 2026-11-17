# 既存のリソース（手動で作成済み）を imports.tf で取り込んだもの。既定値と同じ項目は省略している

resource "azurerm_resource_group" "main" {
  name     = "news-summarizer-rg"
  location = "japaneast"

  # state 用のストレージアカウントも含むため、誤って削除しないようにする
  lifecycle {
    prevent_destroy = true
  }
}

# Container Apps 環境のログの送信先
resource "azurerm_log_analytics_workspace" "main" {
  name                = "news-summarizer-env-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "main" {
  name                       = "news-summarizer-env"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  logs_destination           = "log-analytics"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

# API（FastAPI）。イメージは deploy-backend.yml が更新する
resource "azurerm_container_app" "backend" {
  name                         = "news-summarizer-backend"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  max_inactive_revisions       = 100

  secret {
    name  = "database-url"
    value = var.database_url
  }

  ingress {
    external_enabled = true
    target_port      = 8000

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name = "news-summarizer-backend"
      # 作成時のみ使う値。以降は CI が更新するため ignore_changes で管理から外す
      image  = "ghcr.io/rtssahar-cpu/news-summarizer/backend:ac78df21953400fae9c3ccdd15feb6581ee99f30"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].container[0].image]
  }
}
