// PostgreSQL Flexible Server module - with Entra auth and pgvector

param location string
param serverName string
param subnetId string
param vnetId string
@secure()
param adminPassword string
param entraAdminObjectId string
param entraAdminEmail string

// Private DNS Zone for PostgreSQL
// Note: No environment() suffix available for PostgreSQL; zone name is cloud-specific
resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.postgres.database.azure.com'
  location: 'global'
}

// Link DNS zone to VNet
resource privateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZone
  name: '${serverName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnetId
    }
  }
}

// PostgreSQL Flexible Server
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: serverName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: 'psqladmin'
    administratorLoginPassword: adminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    network: {
      delegatedSubnetResourceId: subnetId
      privateDnsZoneArmResourceId: privateDnsZone.id
    }
    highAvailability: {
      mode: 'Disabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Enabled' // Keep enabled for initial setup, can disable later
    }
  }
}

// Set Entra admin
resource entraAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2023-03-01-preview' = {
  parent: postgresServer
  name: entraAdminObjectId
  properties: {
    principalName: entraAdminEmail
    principalType: 'User'
    tenantId: tenant().tenantId
  }
}

// Enable pgvector extension
resource pgvectorExtension 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresServer
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR,UUID-OSSP'
    source: 'user-override'
  }
}

output serverName string = postgresServer.name
output serverFqdn string = postgresServer.properties.fullyQualifiedDomainName
output serverId string = postgresServer.id
