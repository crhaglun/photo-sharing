# Date Tags Design

## Overview

Photos need date/time metadata for sorting and filtering. Digital photos have reliable EXIF timestamps, but analog scans require manual entry with varying precision.

## Data Model

Date information is stored as a range with two timestamps:

| Field | Description | Example |
|-------|-------------|---------|
| not_earlier_than | Earliest possible date | 1965-07-01 |
| not_later_than | Latest possible date | 1965-07-31 |

### Examples

| Scenario | not_earlier_than | not_later_than |
|----------|------------------|----------------|
| Exact EXIF timestamp | 1965-07-15 10:30:00 | 1965-07-15 10:30:00 |
| Known month | 1965-07-01 | 1965-07-31 |
| Known year | 1965-01-01 | 1965-12-31 |
| "Summer 1965" | 1965-06-01 | 1965-08-31 |
| "Early 1970s" | 1970-01-01 | 1974-12-31 |
| Multi-year range | 1965-01-01 | 1967-12-31 |
| Unknown | null | null |

## Data Sources

### EXIF Timestamp (Automatic)
- Digital photos from cameras/phones have reliable timestamps
- Both range values set to the exact timestamp

### Folder/Filename (Semi-automatic)
- Some scanned photos may be organized in dated folders
- Uploader can extract hints from folder structure
- Range width depends on what can be inferred

### Manual Entry
- User provides start and end dates at whatever granularity is known
- Can be progressively refined (narrow the range) by multiple users
- See [Edit History](edit-history.md) for tracking changes

## Filtering Behavior

Frontend provides a start/end date selector. A photo matches if its date range **intersects** the filter range:

```
Photo matches if: photo.not_later_than >= filter.start
                  AND photo.not_earlier_than <= filter.end
```

Photos with unknown dates (both values null) can optionally be included/excluded via filter toggle.

## Display

Display logic based on range width:

| Condition | Display |
|-----------|---------|
| Same timestamp | "July 15, 1965" |
| Same month | "July 1965" |
| Same year | "1965" |
| Multi-year | "1965 - 1967" |
| Unknown | "Date unknown" |
