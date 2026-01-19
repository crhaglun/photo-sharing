// VPN Gateway module - Point-to-Site VPN

param location string
param vpnGatewayName string
param publicIpName string
param gatewaySubnetId string
param vpnClientAddressPool string

// Public IP for VPN Gateway
resource publicIp 'Microsoft.Network/publicIPAddresses@2023-05-01' = {
  name: publicIpName
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
            id: gatewaySubnetId
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
output vpnGatewayId string = vpnGateway.id
output publicIpAddress string = publicIp.properties.ipAddress
