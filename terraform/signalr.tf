# =============================================================================
# AZURE SIGNALR SERVICE (Push real-time verso la Dashboard via WebSocket)
# =============================================================================

resource "azurerm_signalr_service" "signalr" {
  name                = local.signalr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  sku {
    name     = var.signalr_sku_name
    capacity = 1
  }

  # Modalità Serverless essenziale per architetture basate su Azure Functions
  service_mode = "Serverless"

  cors {
    allowed_origins = ["*"]
  }

  connectivity_logs_enabled = true
  messaging_logs_enabled    = false
  live_trace_enabled        = false

  tags = local.common_tags
}
