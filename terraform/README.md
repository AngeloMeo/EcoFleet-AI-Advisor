# 🏗️ EcoFleet AI Advisor - Infrastructure as Code (Terraform)

Questo modulo contiene l'intera infrastruttura cloud di **EcoFleet AI Advisor** definita tramite **Terraform**, permettendo il provisioning e il teardown automatico 1-click di tutti i servizi su **Microsoft Azure**.

---

## 🏛️ Architettura delle Risorse

| File | Servizio Azure | Dettagli & Ruolo |
|---|---|---|
| [`main.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/main.tf) | Resource Group & Provider | Gestione provider `azurerm` e `random`, definizione Resource Group e blocco backend remoto |
| [`storage.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/storage.tf) | Azure Storage & Queues | Storage Account (`StorageV2`, `Standard_LRS`) con code `advice-queue` e `advice-queue-poison` |
| [`database.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/database.tf) | Azure Cosmos DB (NoSQL) | Account NoSQL con database `EcoFleetDB` e container `Telemetry` (PK: `/vehicle_id`, autoscale 1000 RU) |
| [`iot.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/iot.tf) | Azure IoT Hub | Tier `Free_F1` (in `germanywestcentral`), gestione endpoint Event Hub per D2C e feedback C2D |
| [`signalr.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/signalr.tf) | Azure SignalR Service | Tier `Free_F1` in modalità `Serverless` per push WebSocket live sulla dashboard |
| [`monitoring.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/monitoring.tf) | Log Analytics & App Insights | Log Analytics Workspace e due istanze Application Insights (backend e frontend) |
| [`compute.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/compute.tf) | Web App, Functions & RBAC | App Service Linux (Frontend), Function App Python 3.11 (Backend), Managed Identity e ruoli RBAC |
| [`outputs.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/outputs.tf) | Outputs | Esportazione di URL, endpoint e connection string per l'applicazione e la simulazione |
| [`variables.tf`](file:///c:/Users/Angelo/Desktop/Universita_Codice/CloudComputing/EcoFleet-AI-Advisor/terraform/variables.tf) | Variabili | Parametrizzazione di regioni, SKU, prefissi e chiavi API |

---

## 🚀 Utilizzo Rapido (1-Click)

Dalla root del repository, puoi usare gli script PowerShell automatizzati:

### 1. Creazione Infrastruttura (Deploy)
```powershell
.\scripts\deploy-infra.ps1
```
Lo script si occupa automaticamente di:
1. Autenticarsi su Azure tramite `az login`.
2. Eseguire `terraform init` e `terraform apply`.
3. Popolare in automatico il file `simulation/.env` con la nuova connection string di IoT Hub.
4. Sincronizzare l'endpoint API della Function App in `dashboard/app.js`.

### 2. Eliminazione Completa (Teardown / Zero Costi)
Al termine della demo o del test con un recruiter:
```powershell
.\scripts\destroy-infra.ps1
```
Distrugge tutte le risorse create su Azure e resetta le configurazioni locali, garantendo che non restino costi cloud attivi.

---

## 🛠️ Comandi Terraform Manuali

Se preferisci eseguire direttamente i comandi Terraform:

```bash
cd terraform

# 1. Inizializzazione provider
terraform init

# 2. Verifica del piano di esecuzione
terraform plan

# 3. Applicazione
terraform apply

# 4. Lettura degli output
terraform output
terraform output -raw iothub_service_connection_string

# 5. Distruzione
terraform destroy
```

---

## 🔑 Configurazione Gemini API (Opzionale)

Se vuoi passare la tua chiave API Google per Gemini, crea un file `terraform/terraform.tfvars`:
```hcl
google_api_key = "AIzaSy..."
```
Se la variabile non viene valorizzata, il backend serverless utilizzerà in automatico la logica di fallback rule-based, garantendo che il sistema sia sempre funzionante al 100%.
