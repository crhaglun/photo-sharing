// VPN Gateway - Point-to-Site VPN for developer access
// Deployed separately from main infrastructure (takes 30-45 minutes)

@description('Azure region')
param location string = 'swedencentral'

@description('Base name for resources')
param baseName string = 'photosharing'

@description('VPN client address pool (CIDR)')
param vpnClientAddressPool string = '10.100.0.0/24'

// Variables
var vnetName = 'vnet-${baseName}'
var gatewaySubnetName = 'GatewaySubnet'
var vpnGatewayName = 'vpng-${baseName}'
var vpnPublicIpName = 'pip-${baseName}-vpn'

// Reference existing VNet
resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' existing = {
  name: vnetName
}

// GatewaySubnet (created by networking.bicep, referenced here)
resource gatewaySubnet 'Microsoft.Network/virtualNetworks/subnets@2023-05-01' existing = {
  parent: vnet
  name: gatewaySubnetName
}

// Public IP for VPN Gateway
resource publicIp 'Microsoft.Network/publicIPAddresses@2023-05-01' = {
  name: vpnPublicIpName
  location: location
  sku: {
    name: 'Standard'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
  }
}

// VPN Gateway (Note: takes 30-45 minutes to deploy)
resource vpnGateway 'Microsoft.Network/virtualNetworkGateways@2023-05-01' = {
  name: vpnGatewayName
  location: location
  properties: {
    gatewayType: 'Vpn'
    vpnType: 'RouteBased'
    sku: {
      name: 'VpnGw1'
      tier: 'VpnGw1'
    }
    ipConfigurations: [
      {
        name: 'default'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: gatewaySubnet.id
          }
          publicIPAddress: {
            id: publicIp.id
          }
        }
      }
    ]
    vpnClientConfiguration: {
      vpnClientAddressPool: {
        addressPrefixes: [vpnClientAddressPool]
      }
      vpnClientProtocols: ['OpenVPN']
      vpnAuthenticationTypes: ['AAD']
      aadTenant: '${environment().authentication.loginEndpoint}${tenant().tenantId}/'
      aadAudience: 'c632b3df-fb67-4d84-bdcf-b95ad541b5c8' // Azure VPN Client app ID
      aadIssuer: 'https://sts.windows.net/${tenant().tenantId}/'
    }
  }
}

output vpnGatewayName string = vpnGateway.name
output publicIpAddress string = publicIp.properties.ipAddress
