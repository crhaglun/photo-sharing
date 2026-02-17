// Azure Static Web App - Free tier

param name string
param location string = 'westeurope'

resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: name
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {}
}

output swaName string = staticWebApp.name
output swaDefaultHostname string = staticWebApp.properties.defaultHostname
