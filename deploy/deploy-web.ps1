# Photo Sharing - Frontend Deployment Script
# Builds React app and deploys to Azure Static Web App

param(
    [Parameter(Mandatory=$false)]
    [string]$BaseName = "photosharing"
)

$ErrorActionPreference = "Stop"

# Derived names (must match infra/main.bicep conventions)
$ResourceGroup = "rg-$BaseName"
$ContainerAppName = "ca-$BaseName-api"
$StaticWebAppName = "swa-$BaseName"

Write-Host "Photo Sharing - Frontend Deployment" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Check Azure CLI login
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
Write-Host "Logged in as: $($account.user.name)" -ForegroundColor Green

# Check Node.js
$nodeVersion = node --version 2>$null
if (-not $nodeVersion) {
    Write-Host "Node.js is not installed." -ForegroundColor Red
    exit 1
}
Write-Host "Node.js: $nodeVersion" -ForegroundColor Green

# Resolve paths
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$webDir = Join-Path $repoRoot "src/web"

# Get API URL from Container App
Write-Host "`nRetrieving API URL..." -ForegroundColor Yellow
$apiFqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" -o tsv

if ($LASTEXITCODE -ne 0 -or -not $apiFqdn) {
    Write-Host "Could not retrieve Container App FQDN. Is the API deployed?" -ForegroundColor Red
    exit 1
}
$apiUrl = "https://$apiFqdn"
Write-Host "API URL: $apiUrl" -ForegroundColor Green

# Build frontend with API URL baked in
Write-Host "`nBuilding frontend..." -ForegroundColor Yellow
$env:VITE_API_BASE_URL = $apiUrl

Push-Location $webDir
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }

    npm run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
} finally {
    Pop-Location
}
Write-Host "Frontend built successfully" -ForegroundColor Green

# Get SWA deployment token
Write-Host "`nRetrieving deployment token..." -ForegroundColor Yellow
$deploymentToken = az staticwebapp secrets list `
    --name $StaticWebAppName `
    --resource-group $ResourceGroup `
    --query "properties.apiKey" -o tsv

if ($LASTEXITCODE -ne 0 -or -not $deploymentToken) {
    Write-Host "Could not retrieve SWA deployment token." -ForegroundColor Red
    exit 1
}

# Deploy to Static Web App
Write-Host "`nDeploying to Static Web App..." -ForegroundColor Yellow
$distDir = Join-Path $webDir "dist"

npx @azure/static-web-apps-cli deploy $distDir `
    --deployment-token $deploymentToken `
    --env production

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nDeployment failed!" -ForegroundColor Red
    exit 1
}

# Show the app URL
$swaHostname = az staticwebapp show `
    --name $StaticWebAppName `
    --resource-group $ResourceGroup `
    --query "defaultHostname" -o tsv

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "Frontend URL: https://$swaHostname" -ForegroundColor Cyan
