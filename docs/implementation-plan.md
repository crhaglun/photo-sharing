# Implementation Plan

Iterative approach - each phase delivers working functionality that can be tested before moving on.

## Phase 1: Infrastructure & Database

**Goal:** Azure resources provisioned in private network, VPN access configured, database schema deployed.

**Infrastructure-as-code:** See `infra/` folder. Run `./infra/deploy.ps1` to deploy.

- [x] Create Azure Resource Group
- [x] Create Azure Virtual Network
  - PostgreSQL subnet (with delegation - required by Flexible Server)
  - Private endpoints subnet (no delegation - required for storage)
  - GatewaySubnet for VPN (required by Azure)
- [x] Configure Azure VPN Gateway (Point-to-Site)
  - Generate certificates
  - Configure Azure VPN client
  - Verify VPN connection from dev machine
- [x] Provision Azure Database for PostgreSQL - Flexible Server
  - Deploy into VNet (private access only)
  - Enable Microsoft Entra authentication
  - Enable pgvector extension
  - Add developer account as Entra admin
- [x] Provision Azure Blob Storage account
  - Private endpoint in VNet
  - Create containers: `originals`, `thumbnails`, `default`
  - Assign developer account "Storage Blob Data Contributor" role
- [x] Deploy database schema (all tables from database-schema.md)
- [x] Verify connectivity from dev machine via VPN
  - Authenticate to PostgreSQL with Entra (no password)
  - Authenticate to Blob Storage with Azure CLI credential

**Deliverable:** Private network infrastructure accessible via VPN, using Entra ID / RBAC for all authentication.

**Authentication approach:**
- No connection strings or storage keys
- Developer: Azure CLI credential (own Entra account + RBAC)
- Photo Service: Managed Service Identity + RBAC (configured in Phase 8)

---

## Phase 2: Minimal Uploader

**Goal:** Upload a single photo end-to-end, verify data flows correctly.

- [x] Create uploader project (Python recommended for ML library compatibility)
- [x] Implement SHA-256 hashing
- [x] Implement blob upload (original only, no processing yet)
- [x] Implement photo record creation in database
- [x] Test with a single image

**Deliverable:** One photo in blob storage with corresponding database record.

---

## Phase 3: Image Processing

**Goal:** Generate thumbnails and default view images, extract EXIF.

- [x] Add image resizing (thumbnail: 100px quality=60, default: 2048px quality=92)
- [x] Add EXIF extraction and storage
- [x] Add date extraction (populate not_earlier_than / not_later_than)
  - Priority: folder.yaml → EXIF → file date
- [x] Add folder.yaml sidecar files for date/place configuration
- [x] Update uploader to process all three blob variants
- [x] Add idempotency checks (skip blobs if exist, respect manual edits for metadata)
- [x] Test with a batch of images

**Deliverable:** Processed images with thumbnails, EXIF data in database.

---

## Phase 4: Similarity Embeddings

**Goal:** Generate DINOv2 embeddings for similarity search.

- [ ] Add DINOv2 model loading
- [ ] Generate embeddings for each photo
- [ ] Store in image_embeddings table
- [ ] Add idempotency check
- [ ] Test embedding generation on batch

**Deliverable:** All processed photos have similarity embeddings.

---

## Phase 5: Face Detection

**Goal:** Detect faces and cluster them.

- [ ] Add InsightFace model loading
- [ ] Detect faces, extract bounding boxes and embeddings
- [ ] Store face records in database
- [ ] Run clustering algorithm on all face embeddings
- [ ] Update cluster_id for each face
- [ ] Test on batch, verify clusters make sense

**Deliverable:** Faces detected, clustered, ready for person assignment.

---

## Phase 6: Place Tags (Geocoding)

**Goal:** Extract GPS and reverse geocode to place hierarchy.

- [ ] Add GPS extraction from EXIF
- [ ] Identify reliable GPS sources (by folder/device)
- [ ] Batch reverse geocode via Nominatim
- [ ] Create/lookup places in hierarchy
- [ ] Link photos to places
- [ ] Test on photos with GPS data

**Deliverable:** Photos with GPS have place tags populated.

---

## Phase 7: Full Upload Run

**Goal:** Process entire photo collection.

- [ ] Run uploader on full 18,000 image set
- [ ] Monitor for errors, resume as needed
- [ ] Verify counts (photos, faces, embeddings, places)
- [ ] Spot-check data quality

**Deliverable:** Complete database populated, all blobs uploaded.

---

## Phase 8: Photo Service API

**Goal:** Backend API for frontend consumption.

- [ ] Create dotnet Web API project
- [ ] Configure for Azure Container Apps deployment
- [ ] Implement JWT validation (Firebase tokens)
- [ ] Implement user allowlist check
- [ ] Endpoints:
  - [ ] `GET /photos` - list with filtering (date, place, person, quality)
  - [ ] `GET /photos/{id}` - single photo details
  - [ ] `GET /photos/{id}/thumbnail` - proxy thumbnail blob
  - [ ] `GET /photos/{id}/default` - proxy default view blob
  - [ ] `GET /photos/{id}/original` - proxy original blob (download)
  - [ ] `GET /photos/{id}/similar` - similarity search
  - [ ] `PATCH /photos/{id}` - update metadata (with edit history)
  - [ ] `GET /faces/clusters` - unclustered faces for Faces view
  - [ ] `PATCH /faces/{id}` - assign person to face
  - [ ] `GET /persons` - list all persons
  - [ ] `POST /persons` - create person
- [ ] Deploy to Azure Container Apps
- [ ] Test endpoints with curl/Postman

**Deliverable:** Working API deployed to Azure.

---

## Phase 9: Frontend - Authentication & Library View

**Goal:** Users can log in and browse photos.

- [ ] Create frontend project (React or similar)
- [ ] Integrate Firebase authentication
- [ ] Handle "Request access" for non-allowlisted users
- [ ] Implement Library view
  - Thumbnail grid
  - Infinite scroll
  - Date range filter
  - Place filter
  - Person filter
  - Low-quality toggle
- [ ] Deploy to Azure Static Web Apps (or similar)

**Deliverable:** Users can log in and browse the photo library.

---

## Phase 10: Frontend - Fullscreen View

**Goal:** View and edit individual photos.

- [ ] Implement Fullscreen view
  - Large image display
  - Keyboard navigation (arrow keys, Escape)
  - Download original button
  - EXIF metadata display
- [ ] Implement metadata editing
  - Date range picker
  - Place selector (hierarchical)
  - Person tags
  - Low-quality toggle
- [ ] Implement edit history display
- [ ] Implement "Find similar" feature

**Deliverable:** Full photo viewing and editing experience.

---

## Phase 11: Frontend - Faces View

**Goal:** Map face clusters to people.

- [ ] Implement Faces view
  - Display face clusters
  - Create new person
  - Assign cluster to person
- [ ] Track assignments in edit history

**Deliverable:** Complete face-to-person mapping workflow.

---

## Phase 12: Polish & Hardening

**Goal:** Production-ready deployment.

- [ ] Review and tighten security (CORS, rate limiting)
- [ ] Add error handling and logging
- [ ] Test on mobile devices
- [ ] Performance check on similarity search
- [ ] Document operational procedures (adding users, manual cleanup)
- [ ] Final end-to-end test with family members

**Deliverable:** Production-ready photo sharing service.

---

## Notes

- Each phase should be completed and tested before moving to the next
- The uploader phases (2-7) can run while API/frontend phases (8-12) are developed
- Consider inviting a family member to test after Phase 10 for early feedback
