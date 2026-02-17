// Networking module - VNet with subnets

param location string
param vnetName string
param postgresSubnetName string = 'snet-postgres'
param privateEndpointSubnetName string = 'snet-privateendpoints'
param containerAppSubnetName string = 'snet-containerapp'

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        // Subnet for PostgreSQL (requires delegation)
        name: postgresSubnetName
        properties: {
          addressPrefix: '10.0.0.0/24'
          delegations: [
            {
              name: 'postgresql-delegation'
              properties: {
                serviceName: 'Microsoft.DBforPostgreSQL/flexibleServers'
              }
            }
          ]
        }
      }
      {
        // Subnet for private endpoints (no delegation allowed)
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: '10.0.1.0/24'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        // Subnet for Container Apps Environment (minimum /23)
        name: containerAppSubnetName
        properties: {
          addressPrefix: '10.0.2.0/23'
          delegations: [
            {
              name: 'containerapp-delegation'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        // GatewaySubnet for VPN Gateway (must be named exactly 'GatewaySubnet')
        // Included here so VNet redeployments don't try to remove it
        name: 'GatewaySubnet'
        properties: {
          addressPrefix: '10.0.255.0/27'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output vnetName string = vnet.name
output postgresSubnetId string = vnet.properties.subnets[0].id
output privateEndpointSubnetId string = vnet.properties.subnets[1].id
output containerAppSubnetId string = vnet.properties.subnets[2].id
