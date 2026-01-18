# Place Tags Design

## Overview

Place tags provide location context for photos, with data coming from GPS (when reliable) or manual entry (for analog content).

## Data Model

### Places Table (Hierarchical)

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier |
| name | string | Display name (e.g., "Stockholm") |
| parent_id | UUID | Parent place (e.g., Sweden's ID), null for countries |
| type | enum | `country`, `state`, `city`, `street` |

### Photo → Place Relationship

- Each photo has **one place tag** (single `place_id` reference)
- The place tag can be at any level of the hierarchy
- A photo tagged "Stockholm" is implicitly in "Sweden"

### Filtering Behavior

Filtering by a place includes all photos tagged with that place **or any descendant**:
- Filter by "Sweden" → includes photos tagged Stockholm, Gothenburg, etc.
- Filter by "Stockholm" → only photos tagged Stockholm or places within Stockholm

### Hierarchy Levels

1. **Country** (always applicable)
2. **State/Region** (if applicable)
3. **City** (if applicable)
4. **Street/Location** (if applicable)

Not all levels are required - analog content may only have country-level precision.

## Data Sources

### GPS from EXIF (Automatic)

Reliable GPS data can be determined by:
- **Folder origin**: Assets from iCloud Photos are likely to have reliable GPS
- **Device from EXIF**: iPhone or Android phone indicates reliable GPS

When GPS is available:
- Reverse geocode to extract hierarchical place components during upload
- Store only the resolved place hierarchy (not raw coordinates)
- Coordinates are not needed by the service or frontend

### Manual Entry

For analog content and photos without reliable GPS:
- User selects a single place from the hierarchy
- May be as broad as country only (e.g., just "Sweden")
- Can be refined by changing to a more specific place (e.g., "Stockholm")
- Users can also override GPS-derived locations
- Entered via Fullscreen view editing controls
- All changes tracked in edit history. See [Edit History](edit-history.md).

## Processing Logic (Uploader)

1. Check if source indicates reliable GPS (folder path or device EXIF)
2. If reliable GPS available:
   - Extract coordinates from EXIF
   - Batch reverse geocode to get place hierarchy
   - Find or create place records in database
   - Link photo to the most specific place returned
   - Discard coordinates after processing
3. If no reliable GPS:
   - Leave place tag empty for manual entry later

## Reverse Geocoding

- Performed only during upload preprocessing (batch)
- External geocoding API is acceptable (coordinates only, not images)
- Service and frontend never handle raw coordinates
- Suggested: OpenStreetMap Nominatim (free, no API key required for reasonable volumes)
- Accept whatever the service returns; users can override if needed

## Design Decisions

**Ambiguous geocoding results:**
- Accept whatever the geocoding service returns
- Users can override via manual entry if the result is incorrect

**User overrides:**
- Users can change GPS-derived locations to any place in the hierarchy
- All changes tracked in edit history
