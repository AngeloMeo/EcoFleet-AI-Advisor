<#
.SYNOPSIS
    Deploy rapido 1-Click dell'infrastruttura Azure per EcoFleet AI Advisor tramite Terraform.

.DESCRIPTION
    1. Verifica la presenza di Azure CLI e Terraform.
    2. Esegue 'terraform init' e 'terraform apply'.
    3. Estrae automaticamente gli output (connection string IoT Hub, URL API, URL Dashboard).
    4. Aggiorna automaticamente il file 'simulation/.env' con la nuova connection string di IoT Hub.
    5. Mostra un riepilogo operativo pronto all'uso.

.EXAMPLE
    .\scripts\deploy-infra.ps1
#>

[CmdletBinding()]
param(
    [switch]$AutoApprove = $true
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   EcoFleet AI Advisor - Deploy Rapido Infrastruttura     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verifica Prerequisiti
if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Error "Terraform non e' installato o non e' presente nel PATH di sistema. Scaricalo da https://www.terraform.io/downloads"
}

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI ('az') non e' installato o non e' nel PATH. Scaricalo da https://aka.ms/installazurecliwindows"
}

Write-Host "`n[1/5] Verifica autenticazione Azure..." -ForegroundColor Yellow
$account = az account show --output json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "[WARN] Non risulti autenticato su Azure. Avvio 'az login'..." -ForegroundColor Yellow
    az login
    $account = az account show --output json | ConvertFrom-Json
}
Write-Host "[OK] Autenticato come: $($account.user.name) (Subscription: $($account.name))" -ForegroundColor Green

# 2. Terraform Init
$terraformDir = Join-Path $PSScriptRoot "..\terraform"
Write-Host "`n[2/5] Inizializzazione Terraform (terraform init)..." -ForegroundColor Yellow
Push-Location $terraformDir
try {
    terraform init
    if ($LASTEXITCODE -ne 0) { throw "Errore durante 'terraform init'" }

    # 3. Terraform Apply
    Write-Host "`n[3/5] Creazione infrastruttura Azure (terraform apply)..." -ForegroundColor Yellow
    $applyArgs = @("apply")
    if ($AutoApprove) {
        $applyArgs += "-auto-approve"
    }

    terraform @applyArgs
    if ($LASTEXITCODE -ne 0) { throw "Errore durante 'terraform apply'" }

    # 4. Estrazione Outputs
    Write-Host "`n[4/5] Estrazione endpoint e credenziali..." -ForegroundColor Yellow
    $rgName        = (terraform output -raw resource_group_name 2>$null)
    $funcApiUrl    = (terraform output -raw function_app_api_url 2>$null)
    $webAppUrl     = (terraform output -raw web_app_url 2>$null)
    $iotConnString = (terraform output -raw iothub_service_connection_string 2>$null)
    $iotHostName   = (terraform output -raw iothub_hostname 2>$null)
}
finally {
    Pop-Location
}

# 5. Configurazione automatica di simulation/.env
$simulationEnvPath = Join-Path $PSScriptRoot "..\simulation\.env"
if ($iotConnString) {
    Write-Host "`n[5/5] Configurazione automatica di simulation/.env..." -ForegroundColor Yellow
    $envLines = @(
        "# Generato automaticamente da scripts/deploy-infra.ps1",
        "IOTHUB_SERVICE_CONNECTION_STRING=$iotConnString",
        "IOTHUB_HOSTNAME=$iotHostName"
    )
    $envLines | Set-Content -Path $simulationEnvPath -Encoding UTF8
    Write-Host "[OK] simulation/.env aggiornato con successo!" -ForegroundColor Green
}

# 6. Sincronizzazione automatica dell'endpoint API in dashboard/app.js
$appJsPath = Join-Path $PSScriptRoot "..\dashboard\app.js"
if ((Test-Path $appJsPath) -and $funcApiUrl) {
    Write-Host "[INFO] Sincronizzazione endpoint API in dashboard/app.js..." -ForegroundColor Yellow
    (Get-Content -Path $appJsPath -Encoding UTF8) -replace ": 'https://.*azurewebsites\.net/api'", ": '$funcApiUrl'" |
        Set-Content -Path $appJsPath -Encoding UTF8
    Write-Host "[OK] dashboard/app.js sincronizzato con la nuova Function App!" -ForegroundColor Green
}

# 7. Riepilogo Finale
Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "   INFRASTRUTTURA CREATA E CONFIGURATA CON SUCCESSO!      " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Resource Group Azure: $rgName" -ForegroundColor White
Write-Host "Backend Function API: $funcApiUrl" -ForegroundColor Cyan
Write-Host "Frontend Dashboard:   $webAppUrl" -ForegroundColor Cyan
Write-Host "IoT Hub Host:         $iotHostName" -ForegroundColor White
Write-Host "`nProssimi passi per la demo/test:" -ForegroundColor Yellow
Write-Host "   1. Avvia la simulazione dei veicoli:" -ForegroundColor White
Write-Host "      cd simulation ; python vehicle_emulator.py" -ForegroundColor Gray
Write-Host "   2. Per eliminare tutte le risorse a fine demo ed evitare costi:" -ForegroundColor White
Write-Host "      .\scripts\destroy-infra.ps1`n" -ForegroundColor Gray
