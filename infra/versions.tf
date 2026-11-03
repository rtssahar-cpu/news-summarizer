terraform {
  required_version = "~> 1.17"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 5.12"
    }
  }

  # state はシークレットの値を平文で含むため Azure Storage に置く（ストレージアカウントは手動で作成済み）
  # 認証方法はコードに書かず、環境変数で指定する（dev-vm では ARM_USE_MSI=true でマネージド ID を使う）
  backend "azurerm" {
    subscription_id      = "d1ee2263-cec8-4f97-a7de-86f23ba74f2b"
    resource_group_name  = "news-summarizer-rg"
    storage_account_name = "stnewssumtfstate"
    container_name       = "tfstate"
    key                  = "news-summarizer.tfstate"
  }
}
