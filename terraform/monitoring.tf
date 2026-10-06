# =============================================================================
# MONITORAGGIO: LOG ANALYTICS & APPLICATION INSIGHTS
# =============================================================================

# Workspace Log Analytics centrale per la raccolta dei log e metriche
resource "azurerm_log_analytics_workspace" "workspace" {
  name                = var.use_random_suffix ? "law-${var.project_prefix}-${local.suffix}" : "law-${var.project_prefix}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.common_tags
}

# Application Insights per il Backend (Azure Functions)
resource "azurerm_application_insights" "appinsights_func" {
  name                = local.function_app_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = azurerm_log_analytics_workspace.workspace.id
  application_type    = "web"

  tags = local.common_tags
}

# Application Insights per il Frontend (Web App Dashboard)
resource "azurerm_application_insights" "appinsights_web" {
  name                = local.web_app_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  workspace_id        = azurerm_log_analytics_workspace.workspace.id
  application_type    = "web"

  tags = local.common_tags
}
