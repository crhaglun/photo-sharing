# Implementation Plan

Iterative approach - each phase delivers working functionality that can be tested before moving on.

## Phase 1: Infrastructure & Database

**Goal:** Azure resources provisioned, database schema deployed, basic connectivity verified.

- [ ] Create Azure Resource Group
- [ ] Provision Azure Database for PostgreSQL - Flexible Server
  - Enable pgvector extension
  - Configure firewall for local development
- [ ] Provision Azure Blob Storage account
  - Create containers: `originals`, `thumbnails`, `default`
- [ ] Deploy database schema (all tables from database-schema.md)
- [ ] Verify connectivity from local machine

**Deliverable:** Empty but functional infrastructure.

---

## Phase 2: Minimal Uploader

**Goal:** Upload a single photo end-to-end, verify data flows correctly.

- [ ] Create uploader project (Python recommended for ML library compatibility)
- [ ] Implement SHA-256 hashing
- [ ] Implement blob upload (original only, no processing yet)
- [ ] Implement photo record creation in database
- [ ] Test with a single image

**Deliverable:** One photo in blob storage with corresponding database record.

---

## Phase 3: Image Processing

**Goal:** Generate thumbnails and default view images, extract EXIF.

- [ ] Add image resizing (thumbnail: 100px, default: 2048px)
- [ ] Add EXIF extraction and storage
- [ ] Add date extraction (populate not_earlier_than / not_later_than)
- [ ] Update uploader to process all three blob variants
- [ ] Add idempotency checks (skip if already processed)
- [ ] Test with a batch of ~100 images

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
