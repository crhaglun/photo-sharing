// Photo Sharing - Phase 1 Infrastructure
// Deploys: VNet, VPN Gateway, PostgreSQL, Blob Storage (all private)

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'swedencentral'

@description('Base name for resources')
param baseName string = 'photosharing'

@description('Object ID of the developer user (for RBAC and DB admin)')
param developerObjectId string

@description('Email/UPN of the developer user (for PostgreSQL Entra admin)')
param developerEmail string

@description('VPN client address pool (CIDR)')
param vpnClientAddressPool string = '10.100.0.0/24'

@description('PostgreSQL administrator password (for initial setup, Entra auth used thereafter)')
@secure()
param postgresAdminPassword string

// Variables
var resourceGroupName = 'rg-${baseName}'
var vnetName = 'vnet-${baseName}'
var gatewaySubnetName = 'GatewaySubnet'
var vpnGatewayName = 'vpng-${baseName}'
var vpnPublicIpName = 'pip-${baseName}-vpn'
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
    gatewaySubnetName: gatewaySubnetName
  }
}

// Deploy VPN Gateway
module vpnGateway 'modules/vpn-gateway.bicep' = {
  scope: rg
  name: 'vpnGateway'
  params: {
    location: location
    vpnGatewayName: vpnGatewayName
    publicIpName: vpnPublicIpName
    gatewaySubnetId: networking.outputs.gatewaySubnetId
    vpnClientAddressPool: vpnClientAddressPool
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
output vpnGatewayName string = vpnGateway.outputs.vpnGatewayName
output postgresServerName string = postgres.outputs.serverName
output postgresServerFqdn string = postgres.outputs.serverFqdn
output storageAccountName string = storage.outputs.storageAccountName
