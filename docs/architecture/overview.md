# Architecture Overview

## System Context

This is a service to share photographs from my late father. The set of pictures is static, but there are thousands of manual scans from analog sources (negatives, photo slides) which needs some kind of automated processing with possibility of manual corrections.

For content that originates from analog sources, we have only rough information about when and where the picture was taken, which needs to be provided manually.

Some pictures are close duplicates, i.e. a series of pictures of the same scene. We need the option of marking some pictures as "low quality" and hide them by default.

Consumers of the frontend are generally non-technical, we need the "default" experience to have as few controls as possible.

## High-Level Architecture

- Photo Service (Azure Container App)
  - Public HTTPS endpoint with managed TLS certificate
  - Scale to zero when idle, acceptable cold start (~10 seconds)
  - All incoming requests require valid JWT token
  - Query the database for sets of photos
    - Pagination
    - Sort order
    - Filter by dates, faces, places
  - Proxy content downloads

- Database (Azure Database for PostgreSQL - Flexible Server)
  - Private network service, not exposed to the internet
  - Persists information about photo assets
  - pgvector extension for image similarity search
  - Built-in automated backups
  - See [Database Schema](../design/database-schema.md) for details

- Data storage (Azure Blob Storage)
  - Private network service, not exposed to the internet
  - Blob storage for original media
  - Blob storage for pre-processed thumbnails

- Uploader tool
  - Runs on developer machine
  - Can connect directly to private network with VPN
  - Has permission to update database and blob storage
  - Preprocess assets to create thumbnails and metadata
  - Processing order per photo (idempotent, resumable):
    1. Upload blobs (original, thumbnail, default view)
    2. Create photo record in database
    3. Create image embedding (DINOv2)
    4. Detect faces and create face records (InsightFace)
  - Each step checks if already complete before running
  - See [Image Processing Design](../design/image-processing.md) for details
  - See [Face Recognition Design](../design/face-recognition.md) for detection workflow
  - See [Place Tags Design](../design/place-tags.md) for location extraction
  - See [Date Tags Design](../design/date-tags.md) for timestamp handling

- Frontend
  - Hosted on a service visible to the public internet
  - Login / JWT token creation using existing Firebase account
  - Connects directly to Photo Service Container App
  - See [Frontend Design](../design/frontend.md) for views and controls

## Technology Stack

- Use the Azure stack for hosting
- Azure Container Apps for backend services (managed TLS, scale to zero)
- Azure Database for PostgreSQL - Flexible Server with pgvector extension
- Azure Blob Storage for media files
- Backend services that need custom code should prefer dotnet
- Uploader tool may consist of multiple binaries / scripts that run in phases, it does not have to be a single "do it all" application.

## Backup & Recovery

### Blob Storage
- No backup required
- Source media is backed up externally
- Uploader tool can fully recreate blob storage from source

### Database
- PostgreSQL Flexible Server provides built-in automated backups
- Default retention: 7 days (configurable)
- Uploader tool can recreate initial state (photo metadata, face embeddings)
- Backups preserve: edit history, account allowlist, manual corrections
- Favor simplicity over selective backup strategies

## Key Design Principles

- Do not expose media assets unprotected to the public internet
- Never upload media assets externally for analysis (like running face recognition by uploading images)