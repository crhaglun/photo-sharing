"""Main CLI entry point for the uploader."""

import os
from datetime import datetime, timezone
from pathlib import Path

import click

from .config import Config
from .database import Database
from .folder_metadata import get_folder_metadata, PlaceHint
from .hash import compute_sha256
from .image_processing import process_image, ExifData
from .storage import BlobStorage


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
) -> str | None:
    """Determine place ID for a photo.

    Priority:
    1. EXIF GPS coordinates (reverse geocoding - TODO: implement in Phase 6)
    2. folder.yaml place hierarchy

    Returns:
        Place UUID or None.
    """
    # TODO: Phase 6 will add GPS reverse geocoding
    # For now, skip EXIF GPS and use folder.yaml place hierarchy

    if place_hint and place_hint.has_hierarchy:
        # Use folder.yaml place - for now, use same name for both languages
        # TODO: Could add translation lookup later
        place_id = db.create_place_hierarchy(
            country=(place_hint.country, place_hint.country) if place_hint.country else None,
            state=(place_hint.state, place_hint.state) if place_hint.state else None,
            city=(place_hint.city, place_hint.city) if place_hint.city else None,
            street=(place_hint.street, place_hint.street) if place_hint.street else None,
        )
        return place_id

    return None


@click.group()
def cli():
    """Photo uploader for photo-sharing service."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--root", type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Root directory for folder.yaml inheritance")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def upload(file_path: Path, root: Path | None, verbose: bool):
    """Upload a single photo with full processing.

    FILE_PATH: Path to the photo file to upload.
    """
    config = Config()

    click.echo(f"Processing: {file_path.name}")

    # Get folder metadata
    folder_meta = get_folder_metadata(file_path, root, verbose=verbose)

    # Compute hash
    click.echo("  Computing SHA-256...", nl=False)
    photo_id = compute_sha256(file_path)
    click.echo(f" {photo_id[:12]}...")

    # Process image (resize + EXIF)
    click.echo("  Processing image...", nl=False)
    thumbnail, default_view, exif = process_image(file_path)
    click.echo(" done.")

    # Determine dates
    date_earlier, date_later, date_source = get_date_for_photo(exif, folder_meta.date_range, file_path)

    if date_earlier == date_later:
        click.echo(f"  Date: {date_earlier.date()} (from {date_source})")
    else:
        click.echo(f"  Date: {date_earlier.date()} to {date_later.date()} (from {date_source})")

    # Upload blobs (skip individually if already exist)
    storage = BlobStorage(config.storage_account_name)

    has_original = storage.exists("originals", photo_id)
    has_thumbnail = storage.exists("thumbnails", photo_id)
    has_default = storage.exists("default", photo_id)

    if has_original and has_thumbnail and has_default:
        click.echo("  Blobs: all exist, skipping upload")
    else:
        click.echo(f"  Uploading blobs...", nl=False)
        if not has_original:
            storage.upload_original(file_path, photo_id)
        if not has_thumbnail:
            storage.upload_thumbnail(photo_id, thumbnail)
        if not has_default:
            storage.upload_default(photo_id, default_view)
        click.echo(" done.")

    # Database operations
    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        # Get or create place
        place_id = get_place_id_for_photo(db, exif, folder_meta.place)
        if place_id:
            click.echo(f"  Place: {folder_meta.place.city or folder_meta.place.country}")

        # Create photo record
        click.echo("  Creating database records...", nl=False)
        db.create_photo(
            photo_id=photo_id,
            original_filename=file_path.name,
            date_not_earlier_than=date_earlier,
            date_not_later_than=date_later,
            place_id=place_id,
        )

        # Create EXIF record
        if exif.camera_make or exif.taken_at:
            db.create_exif_metadata(photo_id, exif)

        click.echo(" done.")

    click.echo(f"  Photo ID: {photo_id}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=".jpg,.jpeg,.png", help="Comma-separated file extensions")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed processing information")
def batch(directory: Path, extensions: str, verbose: bool):
    """Upload all photos in a directory with full processing.

    DIRECTORY: Path to directory containing photos.
    """
    config = Config()
    ext_list = [e.strip().lower() for e in extensions.split(",")]

    # Find all matching files
    files = sorted([f for f in directory.rglob("*") if f.suffix.lower() in ext_list])
    click.echo(f"Found {len(files)} files to process")

    storage = BlobStorage(config.storage_account_name)
    processed = 0
    skipped = 0
    errors = 0

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        for i, file_path in enumerate(files, 1):
            click.echo(f"[{i}/{len(files)}] {file_path.relative_to(directory)}")

            try:
                # Get folder metadata (no root limit - allow inheritance from parent folders)
                folder_meta = get_folder_metadata(file_path, root=None, verbose=verbose)

                # Compute hash
                photo_id = compute_sha256(file_path)

                # Check which blobs already exist
                has_original = storage.exists("originals", photo_id)
                has_thumbnail = storage.exists("thumbnails", photo_id)
                has_default = storage.exists("default", photo_id)

                # Process image (needed for EXIF and any missing blobs)
                thumbnail, default_view, exif = process_image(file_path)

                # Determine dates
                date_earlier, date_later, date_source = get_date_for_photo(exif, folder_meta.date_range, file_path)

                if verbose:
                    click.echo(f"  Date: {date_earlier.date()} to {date_later.date()} (from {date_source})")

                # Upload blobs (skip individually if already exist)
                if not has_original:
                    storage.upload_original(file_path, photo_id)
                if not has_thumbnail:
                    storage.upload_thumbnail(photo_id, thumbnail)
                if not has_default:
                    storage.upload_default(photo_id, default_view)

                if verbose and (has_original or has_thumbnail or has_default):
                    click.echo(f"  Blobs: original={'skip' if has_original else 'upload'}, "
                              f"thumbnail={'skip' if has_thumbnail else 'upload'}, "
                              f"default={'skip' if has_default else 'upload'}")

                # Get or create place
                place_id = get_place_id_for_photo(db, exif, folder_meta.place)

                # Create/update records (respects manual edits via has_manual_edits check)
                db.create_photo(
                    photo_id=photo_id,
                    original_filename=file_path.name,
                    date_not_earlier_than=date_earlier,
                    date_not_later_than=date_later,
                    place_id=place_id,
                )

                if exif.camera_make or exif.taken_at:
                    db.create_exif_metadata(photo_id, exif)

                all_blobs_existed = has_original and has_thumbnail and has_default
                status = "updated" if all_blobs_existed else "processed"
                click.echo(f"  {status.capitalize()}: {photo_id[:12]}...")
                processed += 1

            except Exception as e:
                click.echo(f"  Error: {e}", err=True)
                errors += 1

    click.echo(f"\nDone! Processed: {processed}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    cli()
