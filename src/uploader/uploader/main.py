"""Main CLI entry point for the uploader."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

import click

from .config import Config
from .database import Database
from .folder_metadata import get_folder_metadata, PlaceHint
from .hash import compute_sha256
from .image_processing import (
    ExifData,
    create_default_view,
    create_thumbnail,
    extract_exif,
    load_image_with_orientation,
    process_image,
)
from .storage import BlobStorage

if TYPE_CHECKING:
    from .embeddings import DINOv2Embedder
    from .faces import FaceDetector
    from .folder_metadata import FolderMetadata
    from .geocoding import Geocoder


EXTENSIONS_DEFAULT = ".jpg,.jpeg,.png,.heic,.heif"


def find_image_files(directory: Path, extensions: str = EXTENSIONS_DEFAULT) -> list[Path]:
    """Find all image files in a directory recursively."""
    ext_list = [e.strip().lower() for e in extensions.split(",")]
    return sorted(f for f in directory.rglob("*") if f.suffix.lower() in ext_list)


@dataclass
class ProcessingContext:
    """Shared context for photo processing."""

    config: Config
    storage: BlobStorage
    db: Database
    embedder: "DINOv2Embedder | None" = None
    face_detector: "FaceDetector | None" = None
    geocoder: "Geocoder | None" = None
    verbose: bool = False
    # Pre-fetched existence sets for batch optimization
    existing_originals: set[str] | None = None
    existing_thumbnails: set[str] | None = None
    existing_defaults: set[str] | None = None
    existing_photo_ids: set[str] | None = None
    existing_embeddings: set[str] | None = None
    existing_photo_places: dict[str, "UUID"] | None = None
    # Folder metadata cache to avoid redundant filesystem walks
    folder_metadata_cache: dict[Path, "FolderMetadata"] | None = None


def get_date_for_photo(
    exif: ExifData,
    folder_meta_date: "DateRange | None",
    file_path: Path,
) -> tuple[datetime, datetime, str]:
    """Determine date range for a photo.

    Priority:
    1. folder.yaml date range (explicit configuration)
    2. EXIF DateTimeOriginal (use same value for both fields)
    3. File modification date (use same value for both fields)

    Returns:
        Tuple of (not_earlier_than, not_later_than, source) as timezone-aware datetimes.
    """
    from .folder_metadata import DateRange  # avoid circular import

    # Try folder.yaml dates first (explicit configuration takes priority)
    if folder_meta_date and (folder_meta_date.not_earlier_than or folder_meta_date.not_later_than):
        # Convert dates to datetimes
        earlier = (
            datetime.combine(folder_meta_date.not_earlier_than, datetime.min.time(), tzinfo=timezone.utc)
            if folder_meta_date.not_earlier_than
            else None
        )
        later = (
            datetime.combine(folder_meta_date.not_later_than, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc)
            if folder_meta_date.not_later_than
            else None
        )

        # Build source string with path
        source = f"folder.yaml ({folder_meta_date.source_path})" if folder_meta_date.source_path else "folder.yaml"

        # Use what we have
        if earlier and later:
            return earlier, later, source
        elif earlier:
            return earlier, earlier, source
        elif later:
            return later, later, source

    # Try EXIF date
    if exif.taken_at:
        # Make timezone-aware (assume UTC if naive)
        dt = exif.taken_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt, dt, "EXIF"

    # Fall back to file modification date
    mtime = os.path.getmtime(file_path)
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return dt, dt, "file"


def get_place_id_for_photo(
    db: Database,
    exif: ExifData,
    place_hint: PlaceHint | None,
    geocoder: "Geocoder | None" = None,
) -> tuple[str | None, str]:
    """Determine place ID for a photo.

    Priority:
    1. folder.yaml place hierarchy (explicit configuration)
    2. EXIF GPS coordinates (reverse geocoding)

    Args:
        db: Database connection.
        exif: Extracted EXIF data.
        place_hint: Place hint from folder.yaml.
        geocoder: Optional geocoder instance for batch processing.

    Returns:
        Tuple of (place_id, source) where source is 'folder.yaml', 'GPS', or 'none'.
    """


    # Priority 1: folder.yaml place (explicit configuration)
    if place_hint and place_hint.has_hierarchy:
        place_id = db.create_place_hierarchy(
            country=(place_hint.country, place_hint.country) if place_hint.country else None,
            state=(place_hint.state, place_hint.state) if place_hint.state else None,
            city=(place_hint.city, place_hint.city) if place_hint.city else None,
            street=(place_hint.street, place_hint.street) if place_hint.street else None,
        )
        return place_id, "folder.yaml"

    # Priority 2: GPS reverse geocoding
    if geocoder and exif.gps_lat is not None and exif.gps_lon is not None:
        geocoded = geocoder.reverse_geocode(exif.gps_lat, exif.gps_lon)

        if geocoded and geocoded.country:
            place_id = db.create_place_hierarchy(
                country=(geocoded.country.sv, geocoded.country.en) if geocoded.country else None,
                state=(geocoded.state.sv, geocoded.state.en) if geocoded.state else None,
                city=(geocoded.city.sv, geocoded.city.en) if geocoded.city else None,
                street=(geocoded.street.sv, geocoded.street.en) if geocoded.street else None,
            )
            return place_id, "GPS"

    return None, "none"


def process_photo(
    ctx: ProcessingContext,
    file_path: Path,
    folder_yaml_root: Path | None = None,
) -> str:
    """Process a single photo with full pipeline.

    Args:
        ctx: Processing context with models and connections.
        file_path: Path to the photo file.
        folder_yaml_root: Optional root directory for folder.yaml inheritance.

    Returns:
        Photo ID (SHA-256 hash).
    """
    verbose = ctx.verbose

    # Compute hash first (needed for all checks)
    photo_id = compute_sha256(file_path)
    if verbose:
        click.echo(f"  Hash: {photo_id[:12]}...")

    # Early exit: skip if photo is fully processed (batch optimization)
    if ctx.existing_photo_ids is not None and photo_id in ctx.existing_photo_ids:
        # Photo exists in DB - check if all optional processing is done
        needs_embeddings = ctx.embedder and photo_id not in ctx.existing_embeddings
        needs_place = ctx.geocoder and photo_id not in ctx.existing_photo_places

        if not needs_embeddings and not needs_place:
            # Fully processed, skip everything
            if verbose:
                click.echo(f"  Already processed, skipping")
            return photo_id

    # Photo needs processing - get folder metadata
    parent_dir = file_path.parent
    if ctx.folder_metadata_cache is not None and parent_dir in ctx.folder_metadata_cache:
        folder_meta = ctx.folder_metadata_cache[parent_dir]
    else:
        folder_meta = get_folder_metadata(file_path, folder_yaml_root, verbose=verbose)
        # Cache by parent directory
        if ctx.folder_metadata_cache is not None:
            ctx.folder_metadata_cache[parent_dir] = folder_meta

    # Check which blobs already exist (use pre-fetched sets if available)
    if ctx.existing_originals is not None:
        has_original = photo_id in ctx.existing_originals
        has_thumbnail = photo_id in ctx.existing_thumbnails
        has_default = photo_id in ctx.existing_defaults
    else:
        has_original = ctx.storage.exists("originals", photo_id)
        has_thumbnail = ctx.storage.exists("thumbnails", photo_id)
        has_default = ctx.storage.exists("default", photo_id)

    # Optimize: skip expensive image processing if all blobs exist and photo has place
    need_blobs = not (has_original and has_thumbnail and has_default)
    has_place = ctx.existing_photo_places is not None and photo_id in ctx.existing_photo_places

    if need_blobs:
        # Need to generate blobs - do full image processing (includes EXIF extraction)
        thumbnail, default_view, exif = process_image(file_path)
    elif not has_place:
        # Blobs exist but no place yet - need EXIF for potential GPS geocoding
        from .image_processing import extract_exif
        exif = extract_exif(file_path)
        thumbnail = None
        default_view = None
    else:
        # Blobs exist and place exists - skip all image processing
        # Create minimal ExifData for date logic (will use folder.yaml or file mtime)
        exif = ExifData()
        thumbnail = None
        default_view = None

    # Determine dates
    date_earlier, date_later, date_source = get_date_for_photo(exif, folder_meta.date_range, file_path)
    if verbose:
        if date_earlier == date_later:
            click.echo(f"  Date: {date_earlier.date()} (from {date_source})")
        else:
            click.echo(f"  Date: {date_earlier.date()} to {date_later.date()} (from {date_source})")

    # Upload blobs (skip individually if already exist)
    if not has_original:
        ctx.storage.upload_original(file_path, photo_id)
        # Update pre-fetched set if present
        if ctx.existing_originals is not None:
            ctx.existing_originals.add(photo_id)
    if not has_thumbnail and thumbnail is not None:
        ctx.storage.upload_thumbnail(photo_id, thumbnail)
        # Update pre-fetched set if present
        if ctx.existing_thumbnails is not None:
            ctx.existing_thumbnails.add(photo_id)
    if not has_default and default_view is not None:
        ctx.storage.upload_default(photo_id, default_view)
        # Update pre-fetched set if present
        if ctx.existing_defaults is not None:
            ctx.existing_defaults.add(photo_id)

    if verbose and (has_original or has_thumbnail or has_default):
        click.echo(f"  Blobs: original={'skip' if has_original else 'upload'}, "
                  f"thumbnail={'skip' if has_thumbnail else 'upload'}, "
                  f"default={'skip' if has_default else 'upload'}")

    # Get or create place (skip if photo already has a place assigned)
    place_id = None
    place_source = "none"

    # Check if photo already has a place (use pre-fetched data if available)
    if ctx.existing_photo_places is not None and photo_id in ctx.existing_photo_places:
        place_id = ctx.existing_photo_places[photo_id]
        place_source = "existing"
        if verbose:
            click.echo(f"  Place: already assigned (skipping)")
    else:
        # Need to determine place
        if verbose:
            if folder_meta.place and folder_meta.place.has_hierarchy:
                click.echo(f"  Place hint: folder.yaml ({folder_meta.place.city or folder_meta.place.country})")
            elif exif.gps_lat is not None and exif.gps_lon is not None:
                click.echo(f"  GPS coordinates: {exif.gps_lat:.6f}, {exif.gps_lon:.6f}")
                if ctx.geocoder:
                    click.echo("  Geocoding: calling Nominatim...")
                else:
                    click.echo("  Geocoding: disabled (no geocoder)")
            else:
                click.echo("  Place: no folder.yaml hint or GPS coordinates")

        place_id, place_source = get_place_id_for_photo(ctx.db, exif, folder_meta.place, ctx.geocoder)
        if verbose and place_id:
            if place_source == "folder.yaml":
                click.echo(f"  Place: {folder_meta.place.city or folder_meta.place.country} (from folder.yaml)")
            elif place_source == "GPS":
                click.echo(f"  Place: geocoded from GPS")

        # Update pre-fetched dict if present
        if ctx.existing_photo_places is not None and place_id is not None:
            ctx.existing_photo_places[photo_id] = place_id

    # Create/update photo record (respects manual edits via has_manual_edits check)
    ctx.db.create_photo(
        photo_id=photo_id,
        original_filename=file_path.name,
        date_not_earlier_than=date_earlier,
        date_not_later_than=date_later,
        place_id=place_id,
    )

    # Create EXIF record
    if exif.camera_make or exif.taken_at:
        ctx.db.create_exif_metadata(photo_id, exif)

    # Generate embedding if enabled
    if ctx.embedder:
        # Use pre-fetched set if available, otherwise query database
        if ctx.existing_embeddings is not None:
            embedding_exists = photo_id in ctx.existing_embeddings
        else:
            embedding_exists = ctx.db.embedding_exists(photo_id)

        if embedding_exists:
            if verbose:
                click.echo("  Embedding: exists, skipping")
        else:
            with load_image_with_orientation(file_path) as img:
                embedding = ctx.embedder.generate(img)
            ctx.db.create_image_embedding(photo_id, embedding)
            if verbose:
                click.echo("  Embedding: generated")
            # Update pre-fetched set if present
            if ctx.existing_embeddings is not None:
                ctx.existing_embeddings.add(photo_id)

    # Detect faces if enabled
    if ctx.face_detector:
        # Check if face detection has already been run on this photo
        # We track this by checking if the photo exists in the database (since face detection
        # runs after photo creation). The existing_faces set contains photos with at least one
        # face, but we need to skip photos with zero faces too.
        if ctx.existing_photo_ids is not None:
            # In batch mode: skip if photo already exists in DB (face detection already attempted)
            faces_processed = photo_id in ctx.existing_photo_ids
        else:
            # Single file mode: check if faces table has any records
            faces_processed = ctx.db.faces_exist(photo_id)

        if faces_processed:
            if verbose:
                click.echo(f"  Faces: exist, skipping")
        else:
            with load_image_with_orientation(file_path) as img:
                faces = ctx.face_detector.detect(img)
            for face in faces:
                ctx.db.create_face(
                    photo_id=photo_id,
                    bbox_x=face.bbox_x,
                    bbox_y=face.bbox_y,
                    bbox_width=face.bbox_width,
                    bbox_height=face.bbox_height,
                    embedding=face.embedding,
                )
            if verbose:
                click.echo(f"  Faces: {len(faces)} detected")

    return photo_id


@click.group()
def cli():
    """Photo uploader for photo-sharing service."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--root", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Root directory for folder.yaml inheritance")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
@click.option("--no-embeddings", is_flag=True, help="Skip DINOv2 similarity embeddings")
@click.option("--no-faces", is_flag=True, help="Skip face detection")
@click.option("--no-geocoding", is_flag=True, help="Skip GPS reverse geocoding")
def upload(file_path: Path, root: Path | None, verbose: bool, no_embeddings: bool, no_faces: bool, no_geocoding: bool):
    """Upload a single photo with full processing.

    FILE_PATH: Path to the photo file to upload.
    """
    config = Config()

    click.echo(f"Processing: {file_path.name}")

    # Load models
    embedder = None
    if not no_embeddings:
        click.echo("  Loading DINOv2 model...", nl=False)
        from .embeddings import get_embedder
        embedder = get_embedder()
        click.echo(" done.")

    face_detector = None
    if not no_faces:
        click.echo("  Loading InsightFace model...", nl=False)
        from .faces import get_detector
        face_detector = get_detector()
        click.echo(" done.")

    geocoder = None
    if not no_geocoding:
        from .geocoding import get_geocoder
        geocoder = get_geocoder()

    storage = BlobStorage(config.storage_account_name)

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        ctx = ProcessingContext(
            config=config,
            storage=storage,
            db=db,
            embedder=embedder,
            face_detector=face_detector,
            geocoder=geocoder,
            verbose=True,  # Always verbose for single upload
        )

        photo_id = process_photo(ctx, file_path, root)

    click.echo(f"  Photo ID: {photo_id}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=".jpg,.jpeg,.png,.heic,.heif", help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
@click.option("--no-embeddings", is_flag=True, help="Skip DINOv2 similarity embeddings")
@click.option("--no-faces", is_flag=True, help="Skip face detection")
@click.option("--no-geocoding", is_flag=True, help="Skip GPS reverse geocoding")
def batch(directory: Path, extensions: str, verbose: bool, no_embeddings: bool, no_faces: bool, no_geocoding: bool):
    """Upload all photos in a directory with full processing.

    DIRECTORY: Path to directory containing photos.
    """
    config = Config()
    ext_list = [e.strip().lower() for e in extensions.split(",")]

    # Find all matching files
    files = sorted([f for f in directory.rglob("*") if f.suffix.lower() in ext_list])
    click.echo(f"Found {len(files)} files to process")

    # Load models once (expensive)
    embedder = None
    if no_embeddings:
        click.echo("Embeddings: disabled (--no-embeddings)")
    else:
        click.echo("Loading DINOv2 model...", nl=False)
        from .embeddings import get_embedder
        embedder = get_embedder()
        click.echo(" done.")

    face_detector = None
    if no_faces:
        click.echo("Faces: disabled (--no-faces)")
    else:
        click.echo("Loading InsightFace model...", nl=False)
        from .faces import get_detector
        face_detector = get_detector()
        click.echo(" done.")

    geocoder = None
    if no_geocoding:
        click.echo("Geocoding: disabled (--no-geocoding)")
    else:
        from .geocoding import get_geocoder
        geocoder = get_geocoder()

    storage = BlobStorage(config.storage_account_name)
    processed = 0
    errors = 0

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        # Pre-fetch existence data for batch optimization
        click.echo("Pre-fetching existing data for fast resume...", nl=False)
        existing_originals = storage.list_all_blobs("originals")
        existing_thumbnails = storage.list_all_blobs("thumbnails")
        existing_defaults = storage.list_all_blobs("default")
        existing_photo_ids = db.get_all_photo_ids()
        existing_embeddings = db.get_all_embedding_photo_ids() if not no_embeddings else None
        existing_photo_places = db.get_all_photo_places() if not no_geocoding else None
        click.echo(f" done. ({len(existing_photo_ids)} photos, {len(existing_originals)} originals)")

        ctx = ProcessingContext(
            config=config,
            storage=storage,
            db=db,
            embedder=embedder,
            face_detector=face_detector,
            geocoder=geocoder,
            verbose=verbose,
            existing_originals=existing_originals,
            existing_thumbnails=existing_thumbnails,
            existing_defaults=existing_defaults,
            existing_photo_ids=existing_photo_ids,
            existing_embeddings=existing_embeddings,
            existing_photo_places=existing_photo_places,
            folder_metadata_cache={},  # Enable caching for batch processing
        )

        for i, file_path in enumerate(files, 1):
            click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")

            try:
                photo_id = process_photo(ctx, file_path, folder_yaml_root=None)
                click.echo(f"  Processed: {photo_id[:12]}...")
                processed += 1
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
                errors += 1

    click.echo(f"\nDone! Processed: {processed}, Errors: {errors}")


@cli.command()
@click.option("--threshold", default=0.6, help="Clustering distance threshold (lower = stricter)")
@click.option("--min-samples", default=2, help="Minimum faces per cluster")
def cluster(threshold: float, min_samples: int):
    """Run clustering on all detected faces.

    Groups similar faces together using DBSCAN clustering on face embeddings.
    Results are stored in the cluster_id field of the faces table.
    """
    import numpy as np
    from sklearn.cluster import DBSCAN

    config = Config()

    click.echo("Loading face embeddings from database...")

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        face_data = db.get_all_face_embeddings()

        if not face_data:
            click.echo("No faces found in database.")
            return

        click.echo(f"Found {len(face_data)} faces")

        # Extract face IDs and embeddings
        face_ids = [f[0] for f in face_data]
        embeddings = np.array([f[1] for f in face_data])

        # Normalize embeddings for cosine distance
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings_normalized = embeddings / norms

        click.echo(f"Running DBSCAN clustering (threshold={threshold}, min_samples={min_samples})...")

        # DBSCAN with cosine distance (via precomputed distance matrix)
        # For normalized vectors, cosine distance = 1 - cosine similarity
        # And cosine similarity = dot product for normalized vectors
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
        # Clip to handle floating-point precision issues (similarity slightly > 1)
        distance_matrix = np.clip(1 - similarity_matrix, 0, 2)

        clustering = DBSCAN(
            eps=threshold,
            min_samples=min_samples,
            metric="precomputed",
        ).fit(distance_matrix)

        labels = clustering.labels_

        # Count clusters (excluding noise label -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = list(labels).count(-1)

        click.echo(f"Found {n_clusters} clusters, {n_noise} unclustered faces")

        # Update cluster_id for each face
        click.echo("Updating database...", nl=False)
        for face_id, label in zip(face_ids, labels):
            if label != -1:
                db.update_face_cluster(face_id, f"cluster_{label}")
        click.echo(" done.")

        click.echo(f"\nClustering complete!")
        click.echo(f"  Total faces: {len(face_data)}")
        click.echo(f"  Clusters: {n_clusters}")
        click.echo(f"  Unclustered: {n_noise}")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="List individual photo IDs per discrepancy")
def check(verbose: bool):
    """Check integrity across blob storage containers and database tables.

    Compares originals, thumbnails, and default blob containers against the
    photos table and embeddings table to find discrepancies.
    """
    config = Config()
    storage = BlobStorage(config.storage_account_name)

    click.echo("Fetching blob inventories...", nl=False)
    originals_set = storage.list_all_blobs("originals")
    thumbnails_set = storage.list_all_blobs("thumbnails")
    defaults_set = storage.list_all_blobs("default")
    click.echo(" done.")

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        click.echo("Fetching database records...", nl=False)
        db_photos = db.get_all_photo_ids()
        db_embeddings = db.get_all_embedding_photo_ids()
        db_places = db.get_all_photo_places()
        click.echo(" done.")

    click.echo()
    click.echo("=== Counts ===")
    click.echo(f"  Originals:  {len(originals_set)}")
    click.echo(f"  Thumbnails: {len(thumbnails_set)}")
    click.echo(f"  Defaults:   {len(defaults_set)}")
    click.echo(f"  DB photos:  {len(db_photos)}")
    click.echo(f"  Embeddings: {len(db_embeddings)}")
    click.echo(f"  Places:     {len(db_places)}")

    all_blob_ids = originals_set | thumbnails_set | defaults_set

    issues = 0

    def report(label: str, ids: set[str]) -> None:
        nonlocal issues
        if not ids:
            return
        issues += len(ids)
        click.echo(f"\n  {label}: {len(ids)}")
        if verbose:
            for pid in sorted(ids)[:20]:
                click.echo(f"    {pid[:16]}...")
            if len(ids) > 20:
                click.echo(f"    ... and {len(ids) - 20} more")

    click.echo()
    click.echo("=== Blob discrepancies ===")
    report("In originals but missing thumbnail", originals_set - thumbnails_set)
    report("In originals but missing default", originals_set - defaults_set)
    report("Has thumbnail but no original", thumbnails_set - originals_set)
    report("Has default but no original", defaults_set - originals_set)

    click.echo()
    click.echo("=== Blob vs database ===")
    report("In blob storage but not in DB", all_blob_ids - db_photos)
    report("In DB but no original blob", db_photos - originals_set)
    report("In DB but no thumbnail blob", db_photos - thumbnails_set)
    report("In DB but no default blob", db_photos - defaults_set)

    click.echo()
    click.echo("=== Embeddings ===")
    report("Has embedding but no DB record", db_embeddings - db_photos)
    report("In DB but no embedding", db_photos - db_embeddings)

    click.echo()
    if issues == 0:
        click.echo("No issues found.")
    else:
        click.echo(f"Found {issues} total discrepancies.")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def originals(directory: Path, extensions: str, verbose: bool):
    """Upload original photos to blob storage."""
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    storage = BlobStorage(config.storage_account_name)

    click.echo("Fetching existing originals...", nl=False)
    existing = storage.list_all_blobs("originals")
    click.echo(f" {len(existing)} already uploaded")

    uploaded = 0
    skipped = 0
    errors = 0

    for i, file_path in enumerate(files, 1):
        photo_id = compute_sha256(file_path)

        if photo_id in existing:
            skipped += 1
            if verbose:
                click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
            continue

        try:
            click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")
            storage.upload_original(file_path, photo_id)
            existing.add(photo_id)
            uploaded += 1
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            errors += 1

    click.echo(f"\nDone! Uploaded: {uploaded}, Skipped: {skipped}, Errors: {errors}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def thumbnails(directory: Path, extensions: str, verbose: bool):
    """Generate and upload photo thumbnails (100px square crops)."""
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    storage = BlobStorage(config.storage_account_name)

    click.echo("Fetching existing thumbnails...", nl=False)
    existing = storage.list_all_blobs("thumbnails")
    click.echo(f" {len(existing)} already uploaded")

    uploaded = 0
    skipped = 0
    errors = 0

    for i, file_path in enumerate(files, 1):
        photo_id = compute_sha256(file_path)

        if photo_id in existing:
            skipped += 1
            if verbose:
                click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
            continue

        try:
            click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")
            with load_image_with_orientation(file_path) as img:
                data = create_thumbnail(img)
            storage.upload_thumbnail(photo_id, data)
            existing.add(photo_id)
            uploaded += 1
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            errors += 1

    click.echo(f"\nDone! Uploaded: {uploaded}, Skipped: {skipped}, Errors: {errors}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def defaults(directory: Path, extensions: str, verbose: bool):
    """Generate and upload default view images (2048px)."""
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    storage = BlobStorage(config.storage_account_name)

    click.echo("Fetching existing defaults...", nl=False)
    existing = storage.list_all_blobs("default")
    click.echo(f" {len(existing)} already uploaded")

    uploaded = 0
    skipped = 0
    errors = 0

    for i, file_path in enumerate(files, 1):
        photo_id = compute_sha256(file_path)

        if photo_id in existing:
            skipped += 1
            if verbose:
                click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
            continue

        try:
            click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")
            with load_image_with_orientation(file_path) as img:
                data = create_default_view(img)
            storage.upload_default(photo_id, data)
            existing.add(photo_id)
            uploaded += 1
        except Exception as e:
            click.echo(f"  Error: {e}", err=True)
            errors += 1

    click.echo(f"\nDone! Uploaded: {uploaded}, Skipped: {skipped}, Errors: {errors}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--root", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Root directory for folder.yaml inheritance")
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def metadata(directory: Path, root: Path | None, extensions: str, verbose: bool):
    """Create photo and EXIF database records. Uses folder.yaml, EXIF, or file dates."""
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        click.echo("Fetching existing photo records...", nl=False)
        existing = db.get_all_photo_ids()
        click.echo(f" {len(existing)} already in database")

        created = 0
        skipped = 0
        errors = 0
        folder_cache: dict[Path, object] = {}

        for i, file_path in enumerate(files, 1):
            photo_id = compute_sha256(file_path)

            if photo_id in existing:
                skipped += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
                continue

            try:
                click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")

                exif = extract_exif(file_path)

                # Get folder metadata for dates
                parent_dir = file_path.parent
                if parent_dir in folder_cache:
                    folder_meta = folder_cache[parent_dir]
                else:
                    folder_meta = get_folder_metadata(file_path, root, verbose=verbose)
                    folder_cache[parent_dir] = folder_meta

                date_earlier, date_later, date_source = get_date_for_photo(
                    exif, folder_meta.date_range, file_path
                )
                if verbose:
                    if date_earlier == date_later:
                        click.echo(f"  Date: {date_earlier.date()} (from {date_source})")
                    else:
                        click.echo(f"  Date: {date_earlier.date()} to {date_later.date()} (from {date_source})")

                db.create_photo(
                    photo_id=photo_id,
                    original_filename=file_path.name,
                    date_not_earlier_than=date_earlier,
                    date_not_later_than=date_later,
                )

                if exif.camera_make or exif.taken_at:
                    db.create_exif_metadata(photo_id, exif)

                existing.add(photo_id)
                created += 1
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
                errors += 1

    click.echo(f"\nDone! Created: {created}, Skipped: {skipped}, Errors: {errors}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--root", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Root directory for folder.yaml inheritance")
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
@click.option("--no-geocoding", is_flag=True, help="Skip GPS reverse geocoding (folder.yaml only)")
def places(directory: Path, root: Path | None, extensions: str, verbose: bool, no_geocoding: bool):
    """Resolve photo locations from folder.yaml hints and GPS coordinates.

    Requires metadata stage to have been run first.
    """
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    geocoder = None
    if no_geocoding:
        click.echo("Geocoding: disabled (--no-geocoding)")
    else:
        from .geocoding import get_geocoder
        geocoder = get_geocoder()

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        click.echo("Fetching existing data...", nl=False)
        existing_photo_ids = db.get_all_photo_ids()
        existing_places = db.get_all_photo_places()
        click.echo(f" {len(existing_places)} photos already have places")

        resolved = 0
        skipped = 0
        not_in_db = 0
        no_data = 0
        errors = 0
        folder_cache: dict[Path, object] = {}

        for i, file_path in enumerate(files, 1):
            photo_id = compute_sha256(file_path)

            if photo_id not in existing_photo_ids:
                not_in_db += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - not in DB, run metadata first")
                continue

            if photo_id in existing_places:
                skipped += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
                continue

            try:
                parent_dir = file_path.parent
                if parent_dir in folder_cache:
                    folder_meta = folder_cache[parent_dir]
                else:
                    folder_meta = get_folder_metadata(file_path, root, verbose=verbose)
                    folder_cache[parent_dir] = folder_meta

                exif = extract_exif(file_path)
                place_id, place_source = get_place_id_for_photo(db, exif, folder_meta.place, geocoder)

                if place_id:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - {place_source}")
                    db.create_photo(
                        photo_id=photo_id,
                        original_filename=file_path.name,
                        place_id=place_id,
                    )
                    existing_places[photo_id] = place_id
                    resolved += 1
                else:
                    no_data += 1
                    if verbose:
                        click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - no place data")
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
                errors += 1

    click.echo(f"\nDone! Resolved: {resolved}, Skipped: {skipped}, No data: {no_data}, "
               f"Not in DB: {not_in_db}, Errors: {errors}")


@cli.command(name="detect-faces")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def detect_faces(directory: Path, extensions: str, verbose: bool):
    """Detect faces in photos using InsightFace.

    Requires metadata stage to have been run first. Photos that previously had
    zero faces detected will be re-processed.
    """
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    click.echo("Loading InsightFace model...", nl=False)
    from .faces import get_detector
    face_detector = get_detector()
    click.echo(" done.")

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        click.echo("Fetching existing data...", nl=False)
        existing_photo_ids = db.get_all_photo_ids()
        existing_face_photo_ids = db.get_all_face_photo_ids()
        click.echo(f" {len(existing_face_photo_ids)} photos already have faces")

        processed = 0
        skipped = 0
        not_in_db = 0
        errors = 0

        for i, file_path in enumerate(files, 1):
            photo_id = compute_sha256(file_path)

            if photo_id not in existing_photo_ids:
                not_in_db += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - not in DB, run metadata first")
                continue

            if photo_id in existing_face_photo_ids:
                skipped += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
                continue

            try:
                click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}", nl=False)
                with load_image_with_orientation(file_path) as img:
                    faces = face_detector.detect(img)
                for face in faces:
                    db.create_face(
                        photo_id=photo_id,
                        bbox_x=face.bbox_x,
                        bbox_y=face.bbox_y,
                        bbox_width=face.bbox_width,
                        bbox_height=face.bbox_height,
                        embedding=face.embedding,
                    )
                click.echo(f" - {len(faces)} faces")
                if faces:
                    existing_face_photo_ids.add(photo_id)
                processed += 1
            except Exception as e:
                click.echo(f" - Error: {e}", err=True)
                errors += 1

    click.echo(f"\nDone! Processed: {processed}, Skipped: {skipped}, "
               f"Not in DB: {not_in_db}, Errors: {errors}")


@cli.command(name="generate-embeddings")
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=EXTENSIONS_DEFAULT, help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def generate_embeddings(directory: Path, extensions: str, verbose: bool):
    """Generate DINOv2 similarity embeddings for photos.

    Requires metadata stage to have been run first.
    """
    config = Config()
    files = find_image_files(directory, extensions)
    click.echo(f"Found {len(files)} files")

    click.echo("Loading DINOv2 model...", nl=False)
    from .embeddings import get_embedder
    embedder = get_embedder()
    click.echo(" done.")

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        click.echo("Fetching existing data...", nl=False)
        existing_photo_ids = db.get_all_photo_ids()
        existing_embeddings = db.get_all_embedding_photo_ids()
        click.echo(f" {len(existing_embeddings)} photos already have embeddings")

        generated = 0
        skipped = 0
        not_in_db = 0
        errors = 0

        for i, file_path in enumerate(files, 1):
            photo_id = compute_sha256(file_path)

            if photo_id not in existing_photo_ids:
                not_in_db += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - not in DB, run metadata first")
                continue

            if photo_id in existing_embeddings:
                skipped += 1
                if verbose:
                    click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)} - skip")
                continue

            try:
                click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")
                with load_image_with_orientation(file_path) as img:
                    embedding = embedder.generate(img)
                db.create_image_embedding(photo_id, embedding)
                existing_embeddings.add(photo_id)
                generated += 1
            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
                errors += 1

    click.echo(f"\nDone! Generated: {generated}, Skipped: {skipped}, "
               f"Not in DB: {not_in_db}, Errors: {errors}")


if __name__ == "__main__":
    cli()
