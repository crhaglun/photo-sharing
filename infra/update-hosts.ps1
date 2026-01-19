# Photo Sharing - Show Required Hosts File Entries
# Azure wireserver DNS (168.63.129.16) is not accessible from P2S VPN clients,
# so we need manual hosts file entries for private endpoint resolution.

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-photosharing",

    [Parameter(Mandatory=$false)]
    [string]$PostgresServerName = "psql-photosharing",

    [Parameter(Mandatory=$false)]
    [string]$StorageAccountName = "stphotosharing"
)

$ErrorActionPreference = "Stop"

# Check if logged in to Azure
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in to Azure. Running 'az login'..." -ForegroundColor Yellow
    az login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Azure login failed" -ForegroundColor Red
        exit 1
    }
}

# Get PostgreSQL private DNS record name
$pgRecordName = az network private-dns record-set a list `
    --resource-group $ResourceGroup `
    --zone-name "privatelink.postgres.database.azure.com" `
    --query "[0].name" -o tsv 2>$null

if (-not $pgRecordName) {
    Write-Host "Could not find PostgreSQL private DNS record" -ForegroundColor Red
    exit 1
}

# Get PostgreSQL IP
$pgIp = az network private-dns record-set a show `
    --resource-group $ResourceGroup `
    --zone-name "privatelink.postgres.database.azure.com" `
    --name $pgRecordName `
    --query "aRecords[0].ipv4Address" -o tsv

# Get Storage IP
$storageIp = az network private-dns record-set a show `
    --resource-group $ResourceGroup `
    --zone-name "privatelink.blob.core.windows.net" `
    --name $StorageAccountName `
    --query "aRecords[0].ipv4Address" -o tsv 2>$null

Write-Host ""
Write-Host "Add the following lines to C:\Windows\System32\drivers\etc\hosts" -ForegroundColor Cyan
Write-Host "(Edit as Administrator)" -ForegroundColor Cyan
Write-Host ""
Write-Host "# Photo Sharing - Azure Private Endpoints"
Write-Host "$pgIp`t$PostgresServerName.postgres.database.azure.com"
if ($storageIp) {
    Write-Host "$storageIp`t$StorageAccountName.blob.core.windows.net"
}
Write-Host ""
