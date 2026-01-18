# Edit History Design

## Overview

Multiple family members can collaboratively edit photo metadata. Since mistakes are expected and knowledge may be partial (one person knows the country, another fills in the city), we need the ability to track and revert changes.

## Scope

Edit history applies to user-editable metadata:
- Face → Person mappings
- Place tags (country, state, city, street)
- Date/time tags (year, month, day, time)
- Low-quality flag

## Design Principles

- Any allowlisted user can edit metadata (all users trusted)
- Changes are tracked for review and potential reversion
- Supports progressive refinement (partial knowledge filled in over time)
- Simple revert capability for mistakes

## Data Model

### Edit History Record

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Unique identifier for the edit |
| photo_id | UUID | The photo being edited |
| field_type | enum | What was changed: `face_person`, `place`, `date` |
| field_key | string | Specific field (e.g., `place.city`, `date.month`, `face.{face_id}`) |
| old_value | string | Previous value (null if newly set) |
| new_value | string | New value (null if cleared) |
| changed_by | string | User identifier (Firebase UID or email) |
| changed_at | timestamp | When the change was made |

### Example Records

**Face mapping:**
```
photo_id: abc123
field_type: face_person
field_key: face.face_uuid_456
old_value: null
new_value: person_uuid_789  (Uncle Bob)
changed_by: user@example.com
```

**Place refinement:**
```
photo_id: abc123
field_type: place
field_key: place.city
old_value: null
new_value: "Stockholm"
changed_by: cousin@example.com
```

**Date correction:**
```
photo_id: abc123
field_type: date
field_key: date.year
old_value: "1975"
new_value: "1976"
changed_by: user@example.com
```

## Operations

### View Recent Changes
- List recent edits across all photos (for review)
- Filter by user, date range, or field type
- Accessible from Faces view and potentially a dedicated "Recent edits" view

### Revert a Change
- Select a specific edit and revert it
- Creates a new edit record (the revert itself is tracked)
- Does not delete history

## UI Considerations

- Fullscreen view: show edit history for the current photo (who changed what)
- Faces view: show recent face→person assignments for review
- Consider a "Recent changes" summary view (optional, could be deferred)

## Retention

- Retain edit history indefinitely
- Can prune later if storage becomes a concern
- Edit records are small; unlikely to be a problem
