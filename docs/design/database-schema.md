# Database Schema Design

## Overview

This document defines the database schema for the photo sharing service. The schema supports:
- Photo metadata and identity (SHA-256 content hash)
- Hierarchical place tags
- Date ranges with variable precision
- Face detection and person mapping
- Image similarity search
- Collaborative edit history
- User access control

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐
│   places    │◄──────│   photos    │
│  (hierarchy)│       │             │
└──────┬──────┘       └──────┬──────┘
       │                     │
       │ parent_id           │
       ▼                     │
┌─────────────┐              │
│   places    │              │
└─────────────┘              │
                             │
       ┌─────────────────────┼─────────────────────┐
       │                     │                     │
       ▼                     ▼                     ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│    faces    │       │    exif     │       │ embeddings  │
│             │       │             │       │  (DINOv2)   │
└──────┬──────┘       └─────────────┘       └─────────────┘
       │
       │ person_id
       ▼
┌─────────────┐
│   persons   │
└─────────────┘

┌─────────────┐       ┌─────────────┐
│edit_history │       │   users     │
│             │       │ (allowlist) │
└─────────────┘       └─────────────┘
```

## Tables

### photos

Core entity representing a photo asset.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | char(64) | PK | SHA-256 hash of original file |
| original_filename | varchar(255) | NOT NULL | Original filename for reference |
| date_not_earlier_than | timestamp | NULL | Earliest possible date |
| date_not_later_than | timestamp | NULL | Latest possible date |
| place_id | uuid | FK → places.id, NULL | Location tag |
| is_low_quality | boolean | NOT NULL DEFAULT false | Hide from default views |
| created_at | timestamp | NOT NULL | When record was created |
| updated_at | timestamp | NOT NULL | When record was last modified |

**Indexes:**
- `idx_photos_date_range` on (date_not_earlier_than, date_not_later_than) - date filtering
- `idx_photos_place` on (place_id) - place filtering
- `idx_photos_low_quality` on (is_low_quality) - quality filtering

---

### places

Hierarchical location data. Self-referencing for parent-child relationships.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK | Unique identifier |
| name_sv | varchar(255) | NOT NULL | Swedish name (e.g., "Sverige", "Stockholm") |
| name_en | varchar(255) | NOT NULL | English name (e.g., "Sweden", "Stockholm") |
| parent_id | uuid | FK → places.id, NULL | Parent place (null for countries) |
| type | varchar(20) | NOT NULL | `country`, `state`, `city`, `street` |

**Indexes:**
- `idx_places_parent` on (parent_id) - hierarchy traversal
- `idx_places_name_sv` on (name_sv) - search by Swedish name
- `idx_places_name_en` on (name_en) - search by English name
- UNIQUE on (name_sv, parent_id) - no duplicate siblings

**Notes:**
- Filtering by a place must include all descendant places
- Consider materialized path or closure table if hierarchy queries become slow

---

### persons

Named individuals for face tagging.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK | Unique identifier |
| name | varchar(255) | NOT NULL UNIQUE | Person's name |
| created_at | timestamp | NOT NULL | When record was created |

---

### faces

Detected face regions within photos.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK | Unique identifier |
| photo_id | char(64) | FK → photos.id, NOT NULL | Photo containing this face |
| person_id | uuid | FK → persons.id, NULL | Assigned person (null if unassigned) |
| bbox_x | int | NOT NULL | Bounding box X coordinate |
| bbox_y | int | NOT NULL | Bounding box Y coordinate |
| bbox_width | int | NOT NULL | Bounding box width |
| bbox_height | int | NOT NULL | Bounding box height |
| embedding | vector(512) | NOT NULL | InsightFace embedding vector |
| cluster_id | varchar(100) | NULL | Clustering identifier from InsightFace |

**Indexes:**
- `idx_faces_photo` on (photo_id) - get faces for a photo
- `idx_faces_person` on (person_id) - get photos of a person
- `idx_faces_cluster` on (cluster_id) - group faces by cluster

**Notes:**
- Face embeddings stored to avoid expensive reprocessing if upload fails
- Enables re-clustering in the future if needed
- cluster_id helps group similar faces in the Faces view before person assignment

---

### image_embeddings

DINOv2 embeddings for similarity search.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| photo_id | char(64) | PK, FK → photos.id | Photo identifier |
| embedding | vector(768) | NOT NULL | DINOv2 embedding vector |

**Notes:**
- Vector type depends on database (pgvector for PostgreSQL)
- Consider approximate nearest neighbor index (e.g., IVFFlat, HNSW) if collection grows large
- Embedding dimension (768) based on DINOv2 ViT-B/14; adjust if using different model variant

---

### exif_metadata

EXIF data extracted from original files.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| photo_id | char(64) | PK, FK → photos.id | Photo identifier |
| camera_make | varchar(100) | NULL | Camera manufacturer |
| camera_model | varchar(100) | NULL | Camera model |
| lens | varchar(100) | NULL | Lens description |
| focal_length | varchar(20) | NULL | Focal length (e.g., "50mm") |
| aperture | varchar(20) | NULL | Aperture (e.g., "f/2.8") |
| shutter_speed | varchar(20) | NULL | Shutter speed (e.g., "1/250") |
| iso | int | NULL | ISO value |
| taken_at | timestamp | NULL | Original EXIF timestamp |
| raw_exif | jsonb | NULL | Full EXIF data for future use |

**Notes:**
- Commonly displayed fields extracted to columns for easy querying
- raw_exif stores complete EXIF for fields we haven't anticipated

---

### edit_history

Audit log for all user edits to photo metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK | Unique identifier |
| photo_id | char(64) | FK → photos.id, NOT NULL | Photo that was edited |
| field_type | varchar(20) | NOT NULL | `face_person`, `place`, `date`, `quality` |
| field_key | varchar(100) | NOT NULL | Specific field (e.g., `place`, `date.not_earlier_than`, `face.{face_id}`) |
| old_value | text | NULL | Previous value (null if newly set) |
| new_value | text | NULL | New value (null if cleared) |
| changed_by | varchar(255) | NOT NULL | User identifier (Firebase UID) |
| changed_at | timestamp | NOT NULL | When the change was made |

**Indexes:**
- `idx_edit_history_photo` on (photo_id) - get history for a photo
- `idx_edit_history_user` on (changed_by) - get changes by user
- `idx_edit_history_time` on (changed_at DESC) - recent changes

---

### users

Allowlist of users who can access the service.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| firebase_uid | varchar(128) | PK | Firebase user ID |
| email | varchar(255) | NOT NULL UNIQUE | User's email address |
| display_name | varchar(255) | NULL | User's display name |
| created_at | timestamp | NOT NULL | When access was granted |

**Notes:**
- Managed via direct database access (no admin UI)
- JWT validation checks against this table

---

## Common Query Patterns

### Filter photos by date range (intersection)
```sql
SELECT * FROM photos
WHERE date_not_later_than >= :filter_start
  AND date_not_earlier_than <= :filter_end
  AND is_low_quality = false;
```

### Filter photos by place (including descendants)
```sql
WITH RECURSIVE place_tree AS (
  SELECT id FROM places WHERE id = :place_id
  UNION ALL
  SELECT p.id FROM places p
  JOIN place_tree pt ON p.parent_id = pt.id
)
SELECT * FROM photos
WHERE place_id IN (SELECT id FROM place_tree)
  AND is_low_quality = false;
```

### Filter photos by person
```sql
SELECT DISTINCT p.* FROM photos p
JOIN faces f ON f.photo_id = p.id
WHERE f.person_id = :person_id
  AND p.is_low_quality = false;
```

### Find similar photos
```sql
SELECT photo_id, embedding <-> :query_embedding AS distance
FROM image_embeddings
ORDER BY distance
LIMIT 20;
```

### Get edit history for a photo
```sql
SELECT * FROM edit_history
WHERE photo_id = :photo_id
ORDER BY changed_at DESC;
```

---

## Technology

**Database: Azure Database for PostgreSQL - Flexible Server**

- pgvector extension for DINOv2 embedding similarity search
- Recursive CTEs for hierarchical place queries
- JSONB for flexible EXIF storage
- Built-in automated backups
- Burstable B1ms tier sufficient for this workload

**Required extensions:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

## Migration Notes

The uploader tool will need to:
1. Create places on demand during geocoding (avoid duplicates)
2. Create face records during detection/clustering
3. Create embedding records for similarity search
4. Populate exif_metadata from extracted EXIF

The service will need to:
1. Validate JWT and check users table
2. Record all metadata edits to edit_history
3. Support vector similarity queries
