# Frontend Design

## Overview

The frontend provides a simple, accessible interface for non-technical users to browse and view photos.

## Authentication

- Login via existing Firebase account
- JWT token creation for API authentication
- Access restricted to allowlisted accounts
- Users not on the allowlist see a "Request access" message after login
- Allowlist managed via direct database access (no admin UI)

## Views

### Library View (Default)

The main browsing interface with infinite scroll of thumbnails.

**Filtering Controls:**
- Date range
- Person (from face/person tags)
- Place (from place tags)
- Include low-quality photos (toggle, off by default)

**Sorting:**
- Deferred - analog media has ambiguous dates, no meaningful sort order

**Display:**
- Grid of small thumbnails
- Infinite scroll for seamless browsing
- Minimal controls for non-technical users

### Fullscreen View

Entered by pressing a photo in Library view.

**Features:**
- Large representation of the photo (default view image)
- Download original file button
- Navigation controls (forward/back through filtered results)
- Display EXIF metadata (camera, lens, settings) when available
- View edit history for this photo (who changed what)
- "Find similar" - show photos with similar visual content

**Editing Controls:**
- Manually adjust date/date range
- Edit place tags
- Edit people tags
- Mark/unmark as low quality

### Faces View

Administrative view for mapping detected faces to people.

**Features:**
- Groups of detected faces displayed together
- Interface to assign face groups to person tags
- Supports N:1 relationship (multiple face clusters → one person)
  - Content spans ~60 years; same person will have multiple distinct face clusters

## Design Principles

- Default experience should have minimal controls
- Progressive disclosure: advanced features available but not prominent
- Mobile-friendly responsive design

## User Permissions

All allowlisted users are equally trusted:
- Any user can edit metadata (dates, places, people)
- Any user can map faces to people in Faces view
- No separate admin role required
- Mistakes are handled via edit history, not access restrictions. See [Edit History](edit-history.md).

## Low-Quality Flag

Some photos are near-duplicates or lower quality variants of similar shots. These can be manually flagged to hide them from default views.

- Database stores `is_low_quality` boolean flag per photo
- Library view hides low-quality photos by default
- Toggle filter to include them when needed
- Flag can be set/unset in Fullscreen view
- Changes tracked in edit history

## Keyboard Shortcuts (Fullscreen View)

Navigation only:
- Next photo (e.g., arrow right)
- Previous photo (e.g., arrow left)
- Return to library view (e.g., Escape)

No keyboard shortcuts for editing - not meaningful for this use case.
