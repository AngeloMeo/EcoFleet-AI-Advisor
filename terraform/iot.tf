# =============================================================================
# AZURE IOT HUB (D2C Telemetry & C2D Cloud-to-Device Feedback)
# =============================================================================

# Creazione nuovo IoT Hub (creato solo se non viene specificato un hub esistente)
resource "azurerm_iothub" "iot" {
  count               = var.existing_iothub_name == "" ? 1 : 0
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

# Riferimento a IoT Hub preesistente (utilizzato se specificato per riusare lo slot F1 Free)
data "azurerm_iothub" "existing" {
  count               = var.existing_iothub_name != "" ? 1 : 0
  name                = var.existing_iothub_name
  resource_group_name = var.existing_iothub_rg != "" ? var.existing_iothub_rg : azurerm_resource_group.rg.name
}

locals {
  # Istanza attiva dell'IoT Hub (nuova o preesistente)
  iothub_name            = var.existing_iothub_name != "" ? data.azurerm_iothub.existing[0].name : azurerm_iothub.iot[0].name
  iothub_hostname        = var.existing_iothub_name != "" ? data.azurerm_iothub.existing[0].hostname : azurerm_iothub.iot[0].hostname
  iothub_id              = var.existing_iothub_name != "" ? data.azurerm_iothub.existing[0].id : azurerm_iothub.iot[0].id
  iothub_events_endpoint = var.existing_iothub_name != "" ? data.azurerm_iothub.existing[0].event_hub_events_endpoint : azurerm_iothub.iot[0].event_hub_events_endpoint
  iothub_events_path     = var.existing_iothub_name != "" ? data.azurerm_iothub.existing[0].event_hub_events_path : azurerm_iothub.iot[0].event_hub_events_path

  # Cerca la policy iothubowner
  iothub_shared_access_policies = var.existing_iothub_name != "" ? data.azurerm_iothub.existing[0].shared_access_policy : azurerm_iothub.iot[0].shared_access_policy
  iothubowner_policy = [
    for p in local.iothub_shared_access_policies : p if p.key_name == "iothubowner"
  ][0]

  # Connection String del servizio (usata per il provisioning device e C2D da simulation/.env)
  iothub_primary_connection_string = "HostName=${local.iothub_hostname};SharedAccessKeyName=iothubowner;SharedAccessKey=${local.iothubowner_policy.primary_key}"

  # Connection String Event-Hub compatibile richiesta dal trigger di ProcessTelemetry
  iothub_eventhub_connection_string = "Endpoint=sb://${local.iothub_events_endpoint}/;SharedAccessKeyName=iothubowner;SharedAccessKey=${local.iothubowner_policy.primary_key};EntityPath=${local.iothub_events_path}"
}
