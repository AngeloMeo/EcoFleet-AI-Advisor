terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }

  # =========================================================================
  # BACKEND REMOTO (Enterprise Cloud-Native Best Practice)
  # =========================================================================
  # Per ambienti enterprise di produzione, scommenta questo blocco per salvare
  # lo stato condiviso su Azure Blob Storage con State Locking automatico:
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-terraform-state"
  #   storage_account_name = "tfstateecofleet"
  #   container_name       = "tfstate"
  #   key                  = "ecofleet.terraform.tfstate"
  # }
  # =========================================================================
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# Suffisso casuale per garantire l'univocità globale dei nomi DNS su Azure
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  suffix       = random_string.suffix.result
  clean_prefix = replace(lower(var.project_prefix), "/[^a-z0-9]/", "")

  # Nomi con suffisso univoco se abilitato, altrimenti nomi precisi
  resource_group_name  = var.use_random_suffix ? "${var.resource_group_name}-${local.suffix}" : var.resource_group_name
  storage_account_name = var.use_random_suffix ? substr("${local.clean_prefix}${local.suffix}", 0, 24) : replace(lower(var.storage_account_name), "/[^a-z0-9]/", "")
  cosmos_account_name  = var.use_random_suffix ? "${var.cosmos_account_name}-${local.suffix}" : var.cosmos_account_name
  iot_hub_name         = var.use_random_suffix ? "${var.iot_hub_name}-${local.suffix}" : var.iot_hub_name
  signalr_name         = var.use_random_suffix ? "${var.signalr_name}-${local.suffix}" : var.signalr_name
  web_app_name         = var.use_random_suffix ? "${var.web_app_name}-${local.suffix}" : var.web_app_name
  function_app_name    = var.use_random_suffix ? "${var.function_app_name}-${local.suffix}" : var.function_app_name

  common_tags = {
    Project     = "EcoFleet AI Advisor"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

# Gruppo di risorse principale
resource "azurerm_resource_group" "rg" {
  name     = local.resource_group_name
  location = var.location

  tags = local.common_tags
}
