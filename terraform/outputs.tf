# =============================================================================
# OUTPUTS TERRAFORM (Connection String, Endpoint e URL del sistema)
# =============================================================================

output "resource_group_name" {
  description = "Nome del Resource Group creato"
  value       = azurerm_resource_group.rg.name
}

output "function_app_name" {
  description = "Nome della Function App (Backend)"
  value       = azurerm_linux_function_app.function.name
}

output "function_app_default_hostname" {
  description = "Hostname della Function App"
  value       = azurerm_linux_function_app.function.default_hostname
}

output "function_app_api_url" {
  description = "URL base delle API REST della Function App"
  value       = "https://${azurerm_linux_function_app.function.default_hostname}/api"
}

output "web_app_name" {
  description = "Nome dell'App Service (Frontend Dashboard)"
  value       = azurerm_linux_web_app.frontend.name
}

output "web_app_url" {
  description = "URL pubblico della Dashboard Frontend"
  value       = "https://${azurerm_linux_web_app.frontend.default_hostname}"
}

output "iothub_name" {
  description = "Nome di Azure IoT Hub"
  value       = azurerm_iothub.iot.name
}

output "iothub_hostname" {
  description = "Hostname di Azure IoT Hub"
  value       = azurerm_iothub.iot.hostname
}

output "iothub_service_connection_string" {
  description = "Connection String con permessi iothubowner (da inserire in simulation/.env)"
  value       = local.iothub_primary_connection_string
  sensitive   = true
}

output "cosmosdb_endpoint" {
  description = "Endpoint URI dell'account Cosmos DB"
  value       = azurerm_cosmosdb_account.cosmos.endpoint
}

output "storage_account_name" {
  description = "Nome dello Storage Account creato"
  value       = azurerm_storage_account.storage.name
}

output "signalr_service_name" {
  description = "Nome del servizio Azure SignalR"
  value       = azurerm_signalr_service.signalr.name
}

output "appinsights_frontend_connection_string" {
  description = "Connection String di Application Insights per la Dashboard Frontend"
  value       = azurerm_application_insights.appinsights_web.connection_string
  sensitive   = true
}
