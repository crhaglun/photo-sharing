"""Main CLI entry point for the uploader."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import click

from .config import Config
from .database import Database
from .folder_metadata import get_folder_metadata, PlaceHint
from .hash import compute_sha256
from .image_processing import process_image, load_image_with_orientation, ExifData
from .storage import BlobStorage

if TYPE_CHECKING:
    from .embeddings import DINOv2Embedder
    from .faces import FaceDetector
    from .geocoding import Geocoder


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

    # Get folder metadata
    folder_meta = get_folder_metadata(file_path, folder_yaml_root, verbose=verbose)

    # Compute hash
    photo_id = compute_sha256(file_path)
    if verbose:
        click.echo(f"  Hash: {photo_id[:12]}...")

    # Check which blobs already exist
    has_original = ctx.storage.exists("originals", photo_id)
    has_thumbnail = ctx.storage.exists("thumbnails", photo_id)
    has_default = ctx.storage.exists("default", photo_id)

    # Process image (resize + EXIF)
    thumbnail, default_view, exif = process_image(file_path)

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
    if not has_thumbnail:
        ctx.storage.upload_thumbnail(photo_id, thumbnail)
    if not has_default:
        ctx.storage.upload_default(photo_id, default_view)

    if verbose and (has_original or has_thumbnail or has_default):
        click.echo(f"  Blobs: original={'skip' if has_original else 'upload'}, "
                  f"thumbnail={'skip' if has_thumbnail else 'upload'}, "
                  f"default={'skip' if has_default else 'upload'}")

    # Get or create place
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
        if ctx.db.embedding_exists(photo_id):
            if verbose:
                click.echo("  Embedding: exists, skipping")
        else:
            with load_image_with_orientation(file_path) as img:
                embedding = ctx.embedder.generate(img)
            ctx.db.create_image_embedding(photo_id, embedding)
            if verbose:
                click.echo("  Embedding: generated")

    # Detect faces if enabled
    if ctx.face_detector:
        if ctx.db.faces_exist(photo_id):
            if verbose:
                face_count = ctx.db.get_face_count(photo_id)
                click.echo(f"  Faces: {face_count} exist, skipping")
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
        ctx = ProcessingContext(
            config=config,
            storage=storage,
            db=db,
            embedder=embedder,
            face_detector=face_detector,
            geocoder=geocoder,
            verbose=verbose,
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


if __name__ == "__main__":
    cli()
