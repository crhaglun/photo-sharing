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

## Development Conventions

[To be defined as implementation begins]

## Key Commands

[To be defined once the project is set up]
