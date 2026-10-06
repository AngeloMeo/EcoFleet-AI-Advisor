# =============================================================================
# VARIABILI DI PROGETTO E REGIONE
# =============================================================================

variable "project_prefix" {
  description = "Prefisso identificativo del progetto utilizzato per generare i nomi delle risorse"
  type        = string
  default     = "ecofleet"
}

variable "environment" {
  description = "Ambiente di deploy (es. dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Regione Azure primaria per il Resource Group e i servizi"
  type        = string
  default     = "italynorth"
}

variable "iot_hub_location" {
  description = "Regione Azure dedicata a IoT Hub (alcuni piani Free F1 richiedono regioni specifiche)"
  type        = string
  default     = "germanywestcentral"
}

variable "use_random_suffix" {
  description = "Se true, aggiunge un suffisso casuale di 6 caratteri a tutte le risorse per evitare conflitti globali su Azure"
  type        = bool
  default     = false
}

# =============================================================================
# NOMI BASE DELLE RISORSE (Personalizzabili o presi dal setup esistente)
# =============================================================================

variable "resource_group_name" {
  description = "Nome base del Gruppo di Risorse Azure"
  type        = string
  default     = "EcoFleetAdvisor"
}

variable "storage_account_name" {
  description = "Nome base dello Storage Account (solo lettere minuscole e numeri, max 24 car)"
  type        = string
  default     = "storeecofleet"
}

variable "cosmos_account_name" {
  description = "Nome base dell'account Azure Cosmos DB"
  type        = string
  default     = "cosmos-ecofleet"
}

variable "iot_hub_name" {
  description = "Nome base dell'istanza Azure IoT Hub"
  type        = string
  default     = "messagesHub"
}


variable "signalr_name" {
  description = "Nome base del servizio Azure SignalR"
  type        = string
  default     = "signalr-ecofleet"
}

variable "web_app_name" {
  description = "Nome base dell'App Service per la Dashboard frontend"
  type        = string
  default     = "ecofleet"
}

variable "function_app_name" {
  description = "Nome base della Function App per il Backend serverless"
  type        = string
  default     = "func-ecofleet"
}

# =============================================================================
# SKU E TIERS (Default impostati sui piani Free / Serverless a costo zero)
# =============================================================================

variable "storage_account_tier" {
  description = "Tier di performance dello Storage Account"
  type        = string
  default     = "Standard"
}

variable "storage_account_replication" {
  description = "Tipo di replica dello Storage Account"
  type        = string
  default     = "LRS"
}

variable "iot_hub_sku_name" {
  description = "SKU di Azure IoT Hub (F1 = Free, S1 = Standard)"
  type        = string
  default     = "F1"
}

variable "iot_hub_sku_capacity" {
  description = "Numero di unità IoT Hub allocate"
  type        = number
  default     = 1
}

variable "signalr_sku_name" {
  description = "SKU del servizio Azure SignalR (Free_F1 o Standard_S1)"
  type        = string
  default     = "Free_F1"
}

variable "web_app_sku_name" {
  description = "SKU del piano App Service per la dashboard Web (F1 = Free, B1 = Basic)"
  type        = string
  default     = "F1"
}

variable "function_sku_name" {
  description = "SKU del piano App Service per Azure Functions (FC1 = Flex Consumption serverless)"
  type        = string
  default     = "FC1"
}

# =============================================================================
# SEGRETI E CHIAVI API
# =============================================================================

variable "google_api_key" {
  description = "Google Gemini API Key per generare i consigli AI (se lasciata vuota, il backend usa il fallback rule-based)"
  type        = string
  sensitive   = true
  default     = ""
}
