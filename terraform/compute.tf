# =============================================================================
# FRONTEND: APP SERVICE PLAN & WEB APP (Linux - Dashboard Hosting)
# =============================================================================

# Piano App Service Linux per la Dashboard (Piano Free F1 o Basic B1)
resource "azurerm_service_plan" "asp_web" {
  name                = var.use_random_suffix ? "asp-web-${local.suffix}" : "ASP-${var.resource_group_name}-web"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = var.web_app_sku_name

  tags = local.common_tags
}

# Web App Linux per la Dashboard Vue.js
resource "azurerm_linux_web_app" "frontend" {
  name                = local.web_app_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.asp_web.id
  https_only          = true

  site_config {
    # F1 Free non supporta Always On (il default Terraform è true)
    always_on = false

    application_stack {
      node_version = "20-lts"
    }
  }

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.appinsights_web.connection_string
  }

  tags = local.common_tags
}

# =============================================================================
# BACKEND: APP SERVICE PLAN & AZURE FUNCTIONS (Python 3.11 Flex Consumption FC1)
# =============================================================================

# Piano di hosting serverless per Azure Functions (FC1 Flex Consumption)
resource "azurerm_service_plan" "asp_func" {
  name                = var.use_random_suffix ? "asp-func-${local.suffix}" : "ASP-${var.resource_group_name}-func"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "FC1"

  tags = local.common_tags
}

# Azure Function App Linux con Python 3.11 in modalità Flex Consumption (FC1)
resource "azurerm_function_app_flex_consumption" "function" {
  name                       = local.function_app_name
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.asp_func.id

  # Storage container per i package di deploy
  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.storage.primary_blob_endpoint}${azurerm_storage_container.func_deploy.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = azurerm_storage_account.storage.primary_access_key

  # Runtime Python 3.11
  runtime_name    = "python"
  runtime_version = "3.11"

  # Scalabilità e memoria
  maximum_instance_count = 100
  instance_memory_in_mb  = 2048

  # Identità Gestita assegnata dal sistema (usata da DefaultAzureCredential in cosmos_client.py e iot_hub.py)
  identity {
    type = "SystemAssigned"
  }

  site_config {
    # CORS: autorizza l'origine del portale Azure e il dominio della Dashboard Web App
    cors {
      allowed_origins = [
        "https://portal.azure.com",
        "https://${azurerm_linux_web_app.frontend.default_hostname}"
      ]
      support_credentials = true
    }
  }

  # Cablaggio automatico delle variabili d'ambiente (App Settings)
  app_settings = {
    "AzureWebJobsStorage"                        = azurerm_storage_account.storage.primary_connection_string
    "IoTHubEventHubName"                         = azurerm_iothub.iot.event_hub_events_path
    "IoTHubEventHubConnectionString"             = local.iothub_eventhub_connection_string
    "CosmosDBConnectionString__accountEndpoint"  = azurerm_cosmosdb_account.cosmos.endpoint
    "CosmosDBConnectionString"                   = "AccountEndpoint=${azurerm_cosmosdb_account.cosmos.endpoint};AccountKey=${azurerm_cosmosdb_account.cosmos.primary_key};"
    "SignalRConnectionString"                    = azurerm_signalr_service.signalr.primary_connection_string
    "AzureStorageQueueConnectionString"          = azurerm_storage_account.storage.primary_connection_string
    "IotHubHostName"                             = azurerm_iothub.iot.hostname
    "GOOGLE_API_KEY"                             = var.google_api_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING"      = azurerm_application_insights.appinsights_func.connection_string
    "ApplicationInsightsAgent_EXTENSION_VERSION" = "~3"
  }

  tags = local.common_tags
}

# =============================================================================
# RBAC: ROLE ASSIGNMENTS PER MANAGED IDENTITY
# =============================================================================

# Assegnazione del ruolo "Cosmos DB Built-in Data Contributor" alla Managed Identity della Function
resource "azurerm_cosmosdb_sql_role_assignment" "func_cosmos_role" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
  role_definition_id  = "${azurerm_cosmosdb_account.cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_function_app_flex_consumption.function.identity[0].principal_id
  scope               = azurerm_cosmosdb_account.cosmos.id
}

# Assegnazione del ruolo "IoT Hub Data Contributor" alla Managed Identity della Function (per C2D Registry Manager)
resource "azurerm_role_assignment" "func_iothub_role" {
  scope                = azurerm_iothub.iot.id
  role_definition_name = "IoT Hub Data Contributor"
  principal_id         = azurerm_function_app_flex_consumption.function.identity[0].principal_id
}

