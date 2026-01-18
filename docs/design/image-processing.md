# Image Processing Design

## Overview

The uploader tool preprocesses images to create optimized versions for web viewing and deduplication.

## Image Variants

### Thumbnails
- Retain original aspect ratio
- Longest side: max 100 pixels
- Format: JPEG (max compatibility)
- Optimize for size (lower quality acceptable)
- Strip EXIF data
- Use case: Library view grid, fast loading

### Default View Images
- Retain original aspect ratio
- Longest side: max 2048 pixels
- Format: JPEG (max compatibility)
- Optimize for quality
- Strip EXIF data
- Use case: Fullscreen view, detail viewing

### Original Files
- Stored unmodified in blob storage (EXIF preserved)
- Available for download by authenticated users

## EXIF Metadata

- Extract EXIF data during upload preprocessing
- Store in database table (not in processed images)
- Display relevant fields in frontend (camera, lens, settings, etc.)
- Enables metadata display without downloading original
- Processed variants have EXIF stripped for smaller file size

## Deduplication & Identity

- Binary deduplication by content hash
- Hash algorithm: SHA-256
- Hash serves as unique identifier for both database and blob storage
- Solves duplicate filename problem (e.g., multiple IMG0001.jpg in source data)
- Duplicates detected before upload to save storage

### Blob Storage Structure

```
originals/{sha256-hash}
thumbnails/{sha256-hash}.jpg
default/{sha256-hash}.jpg
```

## Similarity Search

**Tooling: DINOv2**

Self-supervised vision model that captures visual structure - good for finding "same car in different photos" or similar scenes without explicit tagging.

### Workflow

1. During upload, generate embedding vector for each image using DINOv2
2. Store embeddings in database (required for runtime similarity search)
3. User selects a photo and clicks "find similar"
4. Compute cosine similarity between selected image embedding and all others
5. Return most similar images

### Use Cases

- Find near-duplicate images (photo series of same scene)
- Find images with similar content (same car, same location, same people)

### Note

Both face embeddings (InsightFace) and image embeddings (DINOv2) are stored persistently - face embeddings to avoid expensive reprocessing, image embeddings to enable runtime similarity search.

## Format Decision

JPEG only - no WebP or modern formats. Original files are available for download, so we optimize processed variants for compatibility over cutting-edge compression.
