# Photo Sharing - Bootstrap Database
# Creates the photosharing database. Run once before applying EF migrations.
# Requires: VPN connected, hosts file updated, Azure CLI logged in, psql installed

param(
    [Parameter(Mandatory=$false)]
    [string]$PostgresServer = "psql-photosharing.postgres.database.azure.com",

    [Parameter(Mandatory=$false)]
    [string]$DatabaseName = "photosharing"
)

$ErrorActionPreference = "Stop"

Write-Host "Photo Sharing - Database Bootstrap" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan

# Check for psql
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "psql is not installed." -ForegroundColor Red
    Write-Host "Install with: winget install PostgreSQL.PostgreSQL.17" -ForegroundColor Yellow
    exit 1
}

# Check Azure CLI login and get user principal name
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}
$userPrincipalName = az ad signed-in-user show --query userPrincipalName -o tsv
Write-Host "Logged in as: $userPrincipalName" -ForegroundColor Green

# Get access token for PostgreSQL
Write-Host "`nGetting access token..." -ForegroundColor Yellow
$token = az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv
if (-not $token) {
    Write-Host "Failed to get access token" -ForegroundColor Red
    exit 1
}

# Set environment variable for psql password
$env:PGPASSWORD = $token

# Check if database exists
Write-Host "Checking if database '$DatabaseName' exists..." -ForegroundColor Yellow
$exists = psql "host=$PostgresServer dbname=postgres user=$userPrincipalName sslmode=require" -tAc "SELECT 1 FROM pg_database WHERE datname='$DatabaseName'"

if ($exists -eq "1") {
    Write-Host "Database '$DatabaseName' already exists" -ForegroundColor Green
} else {
    Write-Host "Creating database '$DatabaseName'..." -ForegroundColor Yellow
    psql "host=$PostgresServer dbname=postgres user=$userPrincipalName sslmode=require" -c "CREATE DATABASE $DatabaseName"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Database created successfully" -ForegroundColor Green
    } else {
        Write-Host "Failed to create database" -ForegroundColor Red
        exit 1
    }
}

# Clean up
$env:PGPASSWORD = $null

Write-Host "`nNext step: Apply EF migrations" -ForegroundColor Cyan
Write-Host "  cd src/api/PhotoSharing.Api && dotnet ef database update"
