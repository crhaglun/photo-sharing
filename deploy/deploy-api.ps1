# Photo Sharing - API Deployment Script
# Builds container image in ACR (no local Docker needed) and updates Container App

param(
    [Parameter(Mandatory=$false)]
    [string]$BaseName = "photosharing"
)

$ErrorActionPreference = "Stop"

# Derived names (must match infra/main.bicep conventions)
$ResourceGroup = "rg-$BaseName"
$AcrName = "acr$BaseName" -replace '-', ''
$ContainerAppName = "ca-$BaseName-api"
$ImageName = "photo-api"
$ImageTag = "latest"

Write-Host "Photo Sharing - API Deployment" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

# Check Azure CLI login
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
Write-Host "Logged in as: $($account.user.name)" -ForegroundColor Green

# Resolve paths
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$apiDir = Join-Path $repoRoot "src/api/PhotoSharing.Api"

if (-not (Test-Path (Join-Path $apiDir "Dockerfile"))) {
    Write-Host "Dockerfile not found at $apiDir" -ForegroundColor Red
    exit 1
}

# Build container image in ACR (cloud build, no local Docker required)
Write-Host "`nBuilding container image in ACR..." -ForegroundColor Yellow
$acrLoginServer = az acr show --name $AcrName --resource-group $ResourceGroup --query loginServer -o tsv
$fullImage = "${acrLoginServer}/${ImageName}:${ImageTag}"

az acr build `
    --registry $AcrName `
    --resource-group $ResourceGroup `
    --image "${ImageName}:${ImageTag}" `
    $apiDir

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nImage build failed!" -ForegroundColor Red
    exit 1
}
Write-Host "Image built: $fullImage" -ForegroundColor Green

# Update Container App with new image
Write-Host "`nUpdating Container App..." -ForegroundColor Yellow
az containerapp update `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --image $fullImage

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nContainer App update failed!" -ForegroundColor Red
    exit 1
}

# Show the app URL
$fqdn = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "properties.configuration.ingress.fqdn" -o tsv

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "API URL: https://$fqdn" -ForegroundColor Cyan
