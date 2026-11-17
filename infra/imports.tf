import {
  to = azurerm_resource_group.main
  id = "/subscriptions/d1ee2263-cec8-4f97-a7de-86f23ba74f2b/resourceGroups/news-summarizer-rg"
}

import {
  to = azurerm_log_analytics_workspace.main
  id = "/subscriptions/d1ee2263-cec8-4f97-a7de-86f23ba74f2b/resourceGroups/news-summarizer-rg/providers/Microsoft.OperationalInsights/workspaces/news-summarizer-env-logs"
}

import {
  to = azurerm_container_app_environment.main
  id = "/subscriptions/d1ee2263-cec8-4f97-a7de-86f23ba74f2b/resourceGroups/news-summarizer-rg/providers/Microsoft.App/managedEnvironments/news-summarizer-env"
}

import {
  to = azurerm_container_app.backend
  id = "/subscriptions/d1ee2263-cec8-4f97-a7de-86f23ba74f2b/resourceGroups/news-summarizer-rg/providers/Microsoft.App/containerApps/news-summarizer-backend"
}
