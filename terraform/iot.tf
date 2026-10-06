# =============================================================================
# AZURE IOT HUB (D2C Telemetry & C2D Cloud-to-Device Feedback)
# =============================================================================

resource "azurerm_iothub" "iot" {
  name                = local.iot_hub_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.iot_hub_location

  sku {
    name     = var.iot_hub_sku_name
    capacity = var.iot_hub_sku_capacity
  }

  # F1 Free supporta solo 2 partizioni Event Hub (default Terraform = 4)
  event_hub_partition_count = 2

  tags = local.common_tags
}

locals {
  # Cerca la policy iothubowner tra quelle esportate automaticamente da Azure IoT Hub
  iothubowner_policy = [
    for p in azurerm_iothub.iot.shared_access_policy : p if p.key_name == "iothubowner"
  ][0]

  # Connection String del servizio (usata per il provisioning device e C2D da simulation/.env)
  iothub_primary_connection_string = "HostName=${azurerm_iothub.iot.hostname};SharedAccessKeyName=iothubowner;SharedAccessKey=${local.iothubowner_policy.primary_key}"

  # Connection String Event-Hub compatibile richiesta dal trigger di ProcessTelemetry
  iothub_eventhub_connection_string = "Endpoint=sb://${azurerm_iothub.iot.event_hub_events_endpoint}/;SharedAccessKeyName=iothubowner;SharedAccessKey=${local.iothubowner_policy.primary_key};EntityPath=${azurerm_iothub.iot.event_hub_events_path}"
}
