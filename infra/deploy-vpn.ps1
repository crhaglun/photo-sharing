# Photo Sharing - VPN Gateway Deployment Script
# Deploys Point-to-Site VPN Gateway for developer access
# NOTE: VPN Gateway takes 30-45 minutes to deploy

param(
    [Parameter(Mandatory=$false)]
    [string]$Location = "swedencentral",

    [Parameter(Mandatory=$false)]
    [string]$BaseName = "photosharing"
)

$ErrorActionPreference = "Stop"

$resourceGroupName = "rg-$BaseName"

Write-Host "Photo Sharing - VPN Gateway Deployment" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Check for Azure CLI
Write-Host "`nChecking prerequisites..." -ForegroundColor Yellow

$azVersion = az version 2>$null | ConvertFrom-Json
if (-not $azVersion) {
    Write-Host "Azure CLI is not installed." -ForegroundColor Red
    Write-Host "Install with: winget install Microsoft.AzureCLI" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Azure CLI: $($azVersion.'azure-cli')" -ForegroundColor Green

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

# Verify resource group exists
Write-Host "`nVerifying resource group '$resourceGroupName' exists..." -ForegroundColor Yellow
$rg = az group show --name $resourceGroupName 2>$null | ConvertFrom-Json
if (-not $rg) {
    Write-Host "Resource group '$resourceGroupName' not found." -ForegroundColor Red
    Write-Host "Run deploy.ps1 first to create the base infrastructure." -ForegroundColor Yellow
    exit 1
}
Write-Host "  Resource group found" -ForegroundColor Green

# Confirm deployment
Write-Host "`nDeployment Configuration:" -ForegroundColor Cyan
Write-Host "  Location:       $Location"
Write-Host "  Resource Group: $resourceGroupName"
Write-Host "  VPN Gateway:    vpng-$BaseName"
Write-Host ""
Write-Host "NOTE: VPN Gateway takes 30-45 minutes to deploy." -ForegroundColor Yellow
Write-Host ""

$confirm = Read-Host "Proceed with deployment? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Deployment cancelled" -ForegroundColor Yellow
    exit 0
}

# Run deployment
Write-Host "`nStarting VPN Gateway deployment..." -ForegroundColor Cyan
$startTime = Get-Date

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$templateFile = Join-Path $scriptDir "vpn.bicep"

az deployment group create `
    --resource-group $resourceGroupName `
    --template-file $templateFile `
    --parameters `
        location=$Location `
        baseName=$BaseName `
    --name "vpn-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nVPN Gateway deployment failed!" -ForegroundColor Red
    exit 1
}

$duration = (Get-Date) - $startTime
Write-Host "`nVPN Gateway deployed successfully!" -ForegroundColor Green
Write-Host "Duration: $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Green

# Output next steps
Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Download VPN client configuration:"
Write-Host "   ./infra/get-vpn-config.ps1"
Write-Host ""
Write-Host "2. Install Azure VPN Client from Microsoft Store (if needed) and import the configuration"
Write-Host ""
Write-Host "3. Connect to VPN, then update hosts file:"
Write-Host "   ./infra/update-hosts.ps1"
