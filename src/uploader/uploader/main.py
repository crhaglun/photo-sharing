"""Main CLI entry point for the uploader."""

from pathlib import Path

import click

from .config import Config
from .database import Database
from .hash import compute_sha256
from .storage import BlobStorage


@click.group()
def cli():
    """Photo uploader for photo-sharing service."""
    pass


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def upload(file_path: Path):
    """Upload a single photo.

    FILE_PATH: Path to the photo file to upload.
    """
    config = Config()

    click.echo(f"Processing: {file_path.name}")

    # Compute hash
    click.echo("  Computing SHA-256...", nl=False)
    photo_id = compute_sha256(file_path)
    click.echo(f" {photo_id[:12]}...")

    # Check if already uploaded
    storage = BlobStorage(config.storage_account_name)
    if storage.exists("originals", photo_id):
        click.echo("  Already uploaded to blob storage, skipping upload.")
    else:
        # Upload to blob storage
        click.echo("  Uploading to blob storage...", nl=False)
        storage.upload_original(file_path, photo_id)
        click.echo(" done.")

    # Create database record
    click.echo("  Creating database record...", nl=False)
    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        if db.photo_exists(photo_id):
            click.echo(" already exists.")
        else:
            db.create_photo(photo_id, file_path.name)
            click.echo(" done.")

    click.echo(f"  Photo ID: {photo_id}")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--extensions", default=".jpg,.jpeg,.png", help="Comma-separated file extensions")
def batch(directory: Path, extensions: str):
    """Upload all photos in a directory.

    DIRECTORY: Path to directory containing photos.
    """
    config = Config()
    ext_list = [e.strip().lower() for e in extensions.split(",")]

    # Find all matching files
    files = [f for f in directory.rglob("*") if f.suffix.lower() in ext_list]
    click.echo(f"Found {len(files)} files to process")

    storage = BlobStorage(config.storage_account_name)

    with Database(config.postgres_host, config.postgres_database, config.postgres_user) as db:
        for i, file_path in enumerate(files, 1):
            click.echo(f"[{i}/{len(files)}] {file_path.name}")

            # Compute hash
            photo_id = compute_sha256(file_path)

            # Check if already processed
            if db.photo_exists(photo_id):
                click.echo(f"  Skipping (already in database)")
                continue

            # Upload to blob storage
            if not storage.exists("originals", photo_id):
                storage.upload_original(file_path, photo_id)
                click.echo(f"  Uploaded to blob storage")

            # Create database record
            db.create_photo(photo_id, file_path.name)
            click.echo(f"  Created database record: {photo_id[:12]}...")

    click.echo("Done!")


if __name__ == "__main__":
    cli()
