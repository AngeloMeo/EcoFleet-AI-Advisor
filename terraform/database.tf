# =============================================================================
# AZURE COSMOS DB (NoSQL API)
# =============================================================================

resource "azurerm_cosmosdb_account" "cosmos" {
  name                = local.cosmos_account_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level       = "Session"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
  }

  tags = local.common_tags
}

# Database NoSQL EcoFleetDB
resource "azurerm_cosmosdb_sql_database" "database" {
  name                = "EcoFleetDB"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

# Container Telemetry con Partition Key su /vehicle_id e throughput autoscale 1000 RU
resource "azurerm_cosmosdb_sql_container" "telemetry" {
  name                  = "Telemetry"
  resource_group_name   = azurerm_resource_group.rg.name
  account_name          = azurerm_cosmosdb_account.cosmos.name
  database_name         = azurerm_cosmosdb_sql_database.database.name
  partition_key_paths   = ["/vehicle_id"]
  partition_key_version = 2

  autoscale_settings {
    max_throughput = 1000
  }

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}
