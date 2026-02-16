// Photo Sharing - Phase 1 Infrastructure
// Deploys: VNet, PostgreSQL, Blob Storage (all private)
// VPN Gateway is deployed separately via vpn.bicep

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'swedencentral'

@description('Base name for resources')
param baseName string = 'photosharing'

@description('Object ID of the developer user (for RBAC and DB admin)')
param developerObjectId string

@description('Email/UPN of the developer user (for PostgreSQL Entra admin)')
param developerEmail string

@description('PostgreSQL administrator password (for initial setup, Entra auth used thereafter)')
@secure()
param postgresAdminPassword string

// Variables
var resourceGroupName = 'rg-${baseName}'
var vnetName = 'vnet-${baseName}'
var postgresServerName = 'psql-${baseName}'
var storageAccountName = replace('st${baseName}', '-', '')
var storagePrivateEndpointName = 'pe-${baseName}-storage'

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: resourceGroupName
  location: location
}

// Deploy networking
module networking 'modules/networking.bicep' = {
  scope: rg
  name: 'networking'
  params: {
    location: location
    vnetName: vnetName
  }
}

// Deploy PostgreSQL
module postgres 'modules/postgres.bicep' = {
  scope: rg
  name: 'postgres'
  params: {
    location: location
    serverName: postgresServerName
    subnetId: networking.outputs.postgresSubnetId
    vnetId: networking.outputs.vnetId
    adminPassword: postgresAdminPassword
    entraAdminObjectId: developerObjectId
    entraAdminEmail: developerEmail
  }
}

// Deploy Storage
module storage 'modules/storage.bicep' = {
  scope: rg
  name: 'storage'
  params: {
    location: location
    storageAccountName: storageAccountName
    subnetId: networking.outputs.privateEndpointSubnetId
    vnetId: networking.outputs.vnetId
    privateEndpointName: storagePrivateEndpointName
    developerObjectId: developerObjectId
  }
}

// Outputs
output resourceGroupName string = rg.name
output vnetName string = networking.outputs.vnetName
output postgresServerName string = postgres.outputs.serverName
output postgresServerFqdn string = postgres.outputs.serverFqdn
output storageAccountName string = storage.outputs.storageAccountName
