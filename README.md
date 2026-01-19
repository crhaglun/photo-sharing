# Photo Sharing

A private photo sharing service for sharing a family photo collection with friends and family.

## Overview

This service hosts ~18,000 digitized photos from analog sources (negatives, slides) and digital cameras, providing:

- **Browse & filter** by date, place, and person
- **Face recognition** to find photos of specific people
- **Similarity search** to find related photos
- **Collaborative tagging** with edit history for corrections

## Architecture

- **Frontend**: Web app with Firebase authentication
- **Backend**: .NET API on Azure Container Apps
- **Database**: PostgreSQL with pgvector for similarity search
- **Storage**: Azure Blob Storage

See [docs/architecture/overview.md](docs/architecture/overview.md) for details.

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [Database Schema](docs/design/database-schema.md)
- [Implementation Plan](docs/implementation-plan.md)

## Infrastructure

Infrastructure-as-code (Bicep) is in the `infra/` folder.

```powershell
# Deploy Azure resources
./infra/deploy.ps1
```

Requires Azure CLI and an Azure subscription. See [infra/deploy.ps1](infra/deploy.ps1) for details.

## Status

In design phase. See [implementation plan](docs/implementation-plan.md) for progress.

## License

MIT License - see [LICENSE](LICENSE) for details.
