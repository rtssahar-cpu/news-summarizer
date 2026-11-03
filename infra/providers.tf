provider "azurerm" {
  features {}

  # 別のサブスクリプションへ誤って適用しないよう、明示的に指定する
  subscription_id = "d1ee2263-cec8-4f97-a7de-86f23ba74f2b"
}
