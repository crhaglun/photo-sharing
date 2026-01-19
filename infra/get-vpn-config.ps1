# Photo Sharing - Download VPN Client Configuration
# Downloads the Azure VPN client configuration for import into Azure VPN Client

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-photosharing",

    [Parameter(Mandatory=$false)]
    [string]$GatewayName = "vpng-photosharing",

    [Parameter(Mandatory=$false)]
    [string]$OutputPath = ".\vpn-client-config"
)

$ErrorActionPreference = "Stop"

Write-Host "Photo Sharing - VPN Client Configuration Download" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# Check if logged in
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Azure login failed" -ForegroundColor Red
        exit 1
    }
}

# Check if VPN gateway exists and is ready
Write-Host "`nChecking VPN Gateway status..." -ForegroundColor Yellow
$gateway = az network vnet-gateway show `
    --resource-group $ResourceGroup `
    --name $GatewayName `
    --query "{state:provisioningState}" `
    -o json 2>$null | ConvertFrom-Json

if (-not $gateway) {
    Write-Host "VPN Gateway '$GatewayName' not found in resource group '$ResourceGroup'" -ForegroundColor Red
    exit 1
}

if ($gateway.state -ne "Succeeded") {
    Write-Host "VPN Gateway is still provisioning (state: $($gateway.state))" -ForegroundColor Yellow
    Write-Host "Please wait for deployment to complete and try again." -ForegroundColor Yellow
    exit 1
}

Write-Host "  Gateway status: $($gateway.state)" -ForegroundColor Green

# Generate VPN client configuration
Write-Host "`nGenerating VPN client configuration..." -ForegroundColor Yellow
$url = az network vnet-gateway vpn-client generate `
    --resource-group $ResourceGroup `
    --name $GatewayName `
    --authentication-method EAPTLS `
    -o tsv

if ($LASTEXITCODE -ne 0 -or -not $url) {
    Write-Host "Failed to generate VPN client configuration" -ForegroundColor Red
    exit 1
}

# Download the configuration
$zipPath = "$OutputPath.zip"
Write-Host "Downloading configuration..." -ForegroundColor Yellow
Invoke-WebRequest -Uri $url -OutFile $zipPath

# Extract
if (Test-Path $OutputPath) {
    Remove-Item -Recurse -Force $OutputPath
}
Expand-Archive -Path $zipPath -DestinationPath $OutputPath
Remove-Item $zipPath

# Find the config file
$configFile = Get-ChildItem -Path $OutputPath -Recurse -Filter "azurevpnconfig.xml" | Select-Object -First 1

if ($configFile) {
    Write-Host "`nVPN client configuration downloaded successfully!" -ForegroundColor Green
    Write-Host "`nConfiguration file: $($configFile.FullName)" -ForegroundColor Cyan
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Install Azure VPN Client from Microsoft Store (if not already installed)"
    Write-Host "2. Open Azure VPN Client"
    Write-Host "3. Click '+' then 'Import'"
    Write-Host "4. Select: $($configFile.FullName)"
    Write-Host "5. Click 'Save' then 'Connect'"
    Write-Host "6. Sign in with your Entra account"
} else {
    Write-Host "`nConfiguration extracted to: $OutputPath" -ForegroundColor Green
    Write-Host "Look for azurevpnconfig.xml in the AzureVPN folder" -ForegroundColor Yellow
}
