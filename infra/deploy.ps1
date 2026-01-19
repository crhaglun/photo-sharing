# Photo Sharing - Infrastructure Deployment Script
# Deploys Phase 1 infrastructure using Bicep

param(
    [Parameter(Mandatory=$false)]
    [string]$Location = "swedencentral",

    [Parameter(Mandatory=$false)]
    [string]$BaseName = "photosharing"
)

$ErrorActionPreference = "Stop"

Write-Host "Photo Sharing - Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check for Azure CLI
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

$azVersion = az version 2>$null | ConvertFrom-Json
if (-not $azVersion) {
    Write-Host "Azure CLI is not installed." -ForegroundColor Red
    Write-Host "Install with: winget install Microsoft.AzureCLI" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Azure CLI: $($azVersion.'azure-cli')" -ForegroundColor Green

# Check for Bicep
$bicepVersion = az bicep version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Bicep not found, installing..." -ForegroundColor Yellow
    az bicep install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to install Bicep" -ForegroundColor Red
        exit 1
    }
    $bicepVersion = az bicep version
}
Write-Host "  Bicep: $bicepVersion" -ForegroundColor Green

# Check if logged in
Write-Host "`nChecking Azure login..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Azure login failed" -ForegroundColor Red
        exit 1
    }
    $account = az account show | ConvertFrom-Json
}
Write-Host "  Logged in as: $($account.user.name)" -ForegroundColor Green
Write-Host "  Subscription: $($account.name)" -ForegroundColor Green

# Get developer info
Write-Host "`nGetting developer identity..." -ForegroundColor Yellow
$developerObjectId = az ad signed-in-user show --query id -o tsv
$developerEmail = az ad signed-in-user show --query userPrincipalName -o tsv
Write-Host "  Object ID: $developerObjectId" -ForegroundColor Green
Write-Host "  Email: $developerEmail" -ForegroundColor Green

# Prompt for PostgreSQL admin password
Write-Host "`nPostgreSQL requires an admin password for initial setup." -ForegroundColor Yellow
Write-Host "(Entra authentication will be used thereafter)" -ForegroundColor Gray
$securePassword = Read-Host "Enter PostgreSQL admin password" -AsSecureString
$postgresPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))

if ($postgresPassword.Length -lt 8) {
    Write-Host "Password must be at least 8 characters" -ForegroundColor Red
    exit 1
}

# Confirm deployment
Write-Host "`nDeployment Configuration:" -ForegroundColor Cyan
Write-Host "  Location:     $Location"
Write-Host "  Base Name:    $BaseName"
Write-Host "  Developer:    $developerEmail"
Write-Host ""
Write-Host "This will create:" -ForegroundColor Yellow
Write-Host "  - Resource Group: rg-$BaseName"
Write-Host "  - Virtual Network with VPN Gateway"
Write-Host "  - PostgreSQL Flexible Server (Burstable B1ms)"
Write-Host "  - Storage Account with private endpoint"
Write-Host ""
Write-Host "NOTE: VPN Gateway takes 30-45 minutes to deploy." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Proceed with deployment? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Deployment cancelled" -ForegroundColor Yellow
    exit 0
}

# Run deployment
Write-Host "`nStarting deployment..." -ForegroundColor Cyan
$startTime = Get-Date

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$templateFile = Join-Path $scriptDir "main.bicep"

az deployment sub create `
    --location $Location `
    --template-file $templateFile `
    --parameters `
        location=$Location `
        baseName=$BaseName `
        developerObjectId=$developerObjectId `
        developerEmail=$developerEmail `
        postgresAdminPassword=$postgresPassword `
    --name "photosharing-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nDeployment failed!" -ForegroundColor Red
    exit 1
}

$duration = (Get-Date) - $startTime
Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
Write-Host "Duration: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Green

# Output next steps
Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Download VPN client configuration:"
Write-Host "   ./infra/get-vpn-config.ps1"
Write-Host ""
Write-Host "2. Install Azure VPN Client from Microsoft Store (if needed) and import the configuration"
Write-Host ""
Write-Host "3. Connect to VPN, then test PostgreSQL connection:"
Write-Host "   psql ""host=psql-$BaseName.postgres.database.azure.com dbname=postgres user=$developerEmail sslmode=require"""
Write-Host ""
Write-Host "4. Deploy database schema (see docs/design/database-schema.md)"
