# Photo Sharing

Photo sharing solution to share my late father's collection (~18,000 photos) with friends and family. The asset set is static - no new photos will be added after initial upload.

## Quick Reference

**Infrastructure:**
- Azure Container Apps (Photo Service API, scale to zero)
- Azure Database for PostgreSQL with pgvector
- Azure Blob Storage (originals, thumbnails, default views)
- Firebase Authentication (external)

**Key Technologies:**
- Backend: dotnet
- Uploader: Python (for ML library compatibility)
- Face recognition: InsightFace
- Similarity search: DINOv2
- Reverse geocoding: Nominatim

**Content addressing:** Photos identified by SHA-256 hash of original file.

## Documentation Structure

- `docs/architecture/overview.md` - System architecture (start here)
- `docs/design/database-schema.md` - Database tables and relationships
- `docs/design/` - Feature specifications (frontend, image processing, faces, places, dates, edit history)
- `docs/implementation-plan.md` - Phased implementation checklist

## Design Principles

- Never upload media to external services for analysis
- All users equally trusted; mistakes handled via edit history
- Favor simplicity over sophistication
- Uploader is idempotent and resumable

## Project Structure

```
src/
  api/
    PhotoSharing.Api/       # ASP.NET Core Web API
      Entities/             # EF Core entity models
      Data/                 # DbContext
      Migrations/           # EF Core migrations
```

## Development Conventions

- Entity models in `Entities/` namespace
- Database context in `Data/` namespace
- Photo IDs are SHA-256 hashes (char(64))
- pgvector for face embeddings (512d) and image embeddings (768d)

## Key Commands

```powershell
# Deploy infrastructure (Phase 1)
./infra/deploy.ps1 -Location swedencentral -BaseName photosharing

# Download VPN client configuration (after deployment)
./infra/get-vpn-config.ps1

# Update hosts file with private endpoint IPs (after VPN connected)
./infra/update-hosts.ps1

# Bootstrap database (one-time, requires VPN + psql)
./infra/bootstrap-db.ps1

# Build API
dotnet build src/api

# Create EF migration
cd src/api/PhotoSharing.Api && dotnet ef migrations add <MigrationName>

# Apply migrations to database (requires VPN connection)
cd src/api/PhotoSharing.Api && dotnet ef database update
```
