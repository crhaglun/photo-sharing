# Photo Sharing - Grant Container App Database Access
# Registers the Container App's managed identity as a PostgreSQL Entra user
# and grants it access to all tables and sequences.
# Run once after first API deployment.
# Requires: VPN connected, hosts file updated, Azure CLI logged in, psql installed

param(
    [Parameter(Mandatory=$false)]
    [string]$BaseName = "photosharing"
)

$ErrorActionPreference = "Stop"

$PostgresServer = "psql-$BaseName.postgres.database.azure.com"
$DatabaseName = "photosharing"
$ContainerAppName = "ca-$BaseName-api"
$ResourceGroup = "rg-$BaseName"

Write-Host "Photo Sharing - Grant Container App DB Access" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# Check for psql
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "psql is not installed." -ForegroundColor Red
    Write-Host "Install with: winget install PostgreSQL.PostgreSQL.17" -ForegroundColor Yellow
    exit 1
}

# Check Azure CLI login
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}
$userPrincipalName = az ad signed-in-user show --query userPrincipalName -o tsv
Write-Host "Logged in as: $userPrincipalName" -ForegroundColor Green

# Verify the Container App exists and has a managed identity
Write-Host "`nVerifying Container App managed identity..." -ForegroundColor Yellow
$principalId = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --query "identity.principalId" -o tsv 2>$null

if (-not $principalId) {
    Write-Host "Container App '$ContainerAppName' not found or has no managed identity." -ForegroundColor Red
    Write-Host "Deploy the infrastructure first: ./infra/deploy.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Container App: $ContainerAppName" -ForegroundColor Green
Write-Host "  Principal ID:  $principalId" -ForegroundColor Green

# Get access token for PostgreSQL
Write-Host "`nGetting access token..." -ForegroundColor Yellow
$token = az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv
if (-not $token) {
    Write-Host "Failed to get access token. Are you connected to the VPN?" -ForegroundColor Red
    exit 1
}
$env:PGPASSWORD = $token

$connString = "host=$PostgresServer dbname=$DatabaseName user=$userPrincipalName sslmode=require"

# Register the managed identity as a PostgreSQL Entra role
Write-Host "`nRegistering '$ContainerAppName' as PostgreSQL Entra user..." -ForegroundColor Yellow
$createRoleSql = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$ContainerAppName') THEN
        CREATE ROLE "$ContainerAppName" LOGIN;
    END IF;
END
`$`$;
SECURITY LABEL FOR "pgaadauth" ON ROLE "$ContainerAppName" IS 'aadauth,oid=$principalId,type=service';
"@
psql $connString -c $createRoleSql
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create Entra principal" -ForegroundColor Red
    $env:PGPASSWORD = $null
    exit 1
}

# Grant access to all tables and sequences
Write-Host "Granting permissions..." -ForegroundColor Yellow
psql $connString -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO `"$ContainerAppName`";"
psql $connString -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO `"$ContainerAppName`";"
psql $connString -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO `"$ContainerAppName`";"
psql $connString -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO `"$ContainerAppName`";"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to grant permissions" -ForegroundColor Red
    $env:PGPASSWORD = $null
    exit 1
}

# Clean up
$env:PGPASSWORD = $null

Write-Host "`nDone! Container App '$ContainerAppName' can now access the database." -ForegroundColor Green
Write-Host "`nNext step: Deploy the API" -ForegroundColor Cyan
Write-Host "  ./deploy/deploy-api.ps1" -ForegroundColor Cyan
