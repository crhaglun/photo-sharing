# Face Recognition Design

## Overview

Face recognition runs locally during the upload preprocessing phase to detect and cluster faces, enabling photo filtering by person.

## Privacy Constraint

Per architecture principles: Never upload media assets externally for analysis. All face recognition must run locally.

## Data Model

### Face
- Unique identifier for a detected face region
- Bounding box coordinates in the source image
- Embedding vector for similarity matching
- Link to source photo

### Person
- Named individual (e.g., "John Smith")
- Can have multiple faces linked to them

### Relationship
- Face → Person is N:1
- Multiple face clusters can map to one person
- This is necessary because:
  - Content spans ~60 years
  - Same individual's appearance changes significantly over time
  - Recognition algorithms may create separate clusters for different ages

## Workflow

1. **Detection**: Uploader scans images for faces
2. **Embedding**: Generate embedding vector for each face
3. **Clustering**: Group similar faces together
4. **Storage**: Save face metadata and embeddings to database
5. **Manual Mapping**: User maps face clusters to person tags via Faces view

All face→person mapping changes are tracked in edit history. See [Edit History](edit-history.md).

## Tooling

**Selected: InsightFace**

Rationale:
- Uses ArcFace embeddings with state-of-the-art accuracy
- Outperforms dlib-based solutions in benchmarks
- Better handling of challenging cases (varying ages, lighting, angles)
- Important for a collection spanning ~60 years where individuals age significantly
- Runs locally (satisfies privacy constraint)
- Accuracy prioritized over speed

Selection criteria:
- Favor accuracy over speed
- Number of discrete faces in asset set is unknown

## Design Decisions

**Photos without visible faces:**
- Skip face processing entirely
- Many photos are nature or architecture with no faces
- These photos simply have no face data associated

**Embedding vectors:**
- Store embeddings in database to avoid expensive reprocessing
- Enables resuming if upload fails after detection but before clustering
- Enables re-clustering if needed in the future

**Detection thresholds:**
- Minimum face size/quality thresholds to be determined during implementation
- Expect iteration to find appropriate values for this specific collection
