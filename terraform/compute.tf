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
# BACKEND: AZURE FUNCTIONS (Python 3.11 Serverless)
# =============================================================================

# Azure Function App Linux con Python 3.11 e Managed Identity abilitata
# Condivide lo stesso App Service Plan Linux (asp_web) della Dashboard per:
# 1. Rimanere 100% Free F1 senza eccedere la quota di piani gratuiti per sottoscrizione/regione
# 2. Rimanere in un unico Resource Group, evitando incompatibilità tra SKU Dynamic e Dedicated
resource "azurerm_linux_function_app" "function" {
  name                       = local.function_app_name
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.asp_web.id
  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key
  https_only                 = true

  # Identità Gestita assegnata dal sistema (usata da DefaultAzureCredential in cosmos_client.py e iot_hub.py)
  identity {
    type = "SystemAssigned"
  }

  site_config {
    # F1 Free non supporta Always On (il default per piani dedicati è true)
    always_on = false

    application_stack {
      python_version = "3.11"
    }

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
    "FUNCTIONS_WORKER_RUNTIME"                   = "python"
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
  principal_id        = azurerm_linux_function_app.function.identity[0].principal_id
  scope               = azurerm_cosmosdb_account.cosmos.id
}

# Assegnazione del ruolo "IoT Hub Data Contributor" alla Managed Identity della Function (per C2D Registry Manager)
resource "azurerm_role_assignment" "func_iothub_role" {
  scope                = azurerm_iothub.iot.id
  role_definition_name = "IoT Hub Data Contributor"
  principal_id         = azurerm_linux_function_app.function.identity[0].principal_id
}

