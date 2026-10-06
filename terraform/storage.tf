# =============================================================================
# AZURE STORAGE ACCOUNT & QUEUES
# =============================================================================

resource "azurerm_storage_account" "storage" {
  name                     = local.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = var.storage_account_tier
  account_replication_type = var.storage_account_replication
  account_kind             = "StorageV2"
  min_tls_version          = "TLS1_2"

  tags = local.common_tags
}

# Coda Azure Storage per il disaccoppiamento asincrono tra ProcessTelemetry e GenerateAdvice
resource "azurerm_storage_queue" "advice_queue" {
  name               = "advice-queue"
  storage_account_id = azurerm_storage_account.storage.id
}

# Coda Poison per messaggi non elaborabili (dead-letter queue)
resource "azurerm_storage_queue" "advice_queue_poison" {
  name               = "advice-queue-poison"
  storage_account_id = azurerm_storage_account.storage.id
}
