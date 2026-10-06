<#
.SYNOPSIS
    Eliminazione sicura 1-Click di tutte le risorse Azure create da Terraform per EcoFleet AI Advisor.

.DESCRIPTION
    1. Richiede conferma all'utente (a meno che non venga specificato il flag -Force).
    2. Esegue 'terraform destroy'.
    3. Resetta 'simulation/.env'.

.EXAMPLE
    .\scripts\destroy-infra.ps1
    .\scripts\destroy-infra.ps1 -Force
#>

[CmdletBinding()]
param(
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Red
Write-Host "   EcoFleet AI Advisor - Teardown Completo (Destroy)      " -ForegroundColor Red
Write-Host "==========================================================" -ForegroundColor Red

if (-not $Force) {
    $confirm = Read-Host "[WARN] Sei sicuro di voler eliminare TUTTE le risorse create su Azure da Terraform? (s/N)"
    if ($confirm -notmatch '^[sSyY]') {
        Write-Host "Operazione annullata." -ForegroundColor Yellow
        exit 0
    }
}

$terraformDir = Join-Path $PSScriptRoot "..\terraform"

Push-Location $terraformDir
try {
    Write-Host "`nEsecuzione di terraform destroy..." -ForegroundColor Yellow
    terraform destroy -auto-approve
    if ($LASTEXITCODE -ne 0) { throw "Errore durante 'terraform destroy'" }
}
finally {
    Pop-Location
}

# Reset simulation/.env
$simulationEnvPath = Join-Path $PSScriptRoot "..\simulation\.env"
if (Test-Path $simulationEnvPath) {
    Set-Content -Path $simulationEnvPath -Value "# Inserisci qui IOTHUB_SERVICE_CONNECTION_STRING dopo il deploy" -Encoding UTF8
    Write-Host "[OK] Reset del file simulation/.env completato." -ForegroundColor Gray
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "   TUTTE LE RISORSE AZURE SONO STATE ELIMINATE!           " -ForegroundColor Green
Write-Host "   (Nessun costo cloud residuo attivo)                    " -ForegroundColor Green
Write-Host "==========================================================`n" -ForegroundColor Green
