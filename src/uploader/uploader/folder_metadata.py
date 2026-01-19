"""Folder metadata parsing from folder.yaml sidecar files."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml


@dataclass
class DateRange:
    """Date range for photos."""

    not_earlier_than: date | None = None
    not_later_than: date | None = None
    source_path: Path | None = None  # Which folder.yaml this came from


@dataclass
class PlaceHint:
    """Place hint from folder metadata."""

    # Named hierarchy
    country: str | None = None
    state: str | None = None
    city: str | None = None
    street: str | None = None

    # Or GPS coordinates (for reverse geocoding)
    lat: float | None = None
    lon: float | None = None

    @property
    def has_coordinates(self) -> bool:
        return self.lat is not None and self.lon is not None

    @property
    def has_hierarchy(self) -> bool:
        return any([self.country, self.state, self.city, self.street])


@dataclass
class FolderMetadata:
    """Combined metadata from folder.yaml."""

    date_range: DateRange | None = None
    place: PlaceHint | None = None


def parse_date(value: str | None) -> date | None:
    """Parse a date string (YYYY-MM-DD format)."""
    if not value:
        return None
    return date.fromisoformat(value)


def load_folder_yaml(folder: Path) -> FolderMetadata | None:
    """Load folder.yaml from a directory if it exists."""
    yaml_path = folder / "folder.yaml"
    if not yaml_path.exists():
        return None

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return None

    metadata = FolderMetadata()

    # Parse date section
    if "date" in data:
        date_data = data["date"]
        metadata.date_range = DateRange(
            not_earlier_than=parse_date(date_data.get("not_earlier_than")),
            not_later_than=parse_date(date_data.get("not_later_than")),
        )

    # Parse place section
    if "place" in data:
        place_data = data["place"]
        metadata.place = PlaceHint(
            country=place_data.get("country"),
            state=place_data.get("state"),
            city=place_data.get("city"),
            street=place_data.get("street"),
            lat=place_data.get("lat"),
            lon=place_data.get("lon"),
        )

    return metadata


def get_folder_metadata(file_path: Path, root: Path | None = None, verbose: bool = False) -> FolderMetadata:
    """Get merged folder metadata for a file, walking up the directory tree.

    Metadata from closer folders overrides metadata from parent folders.

    Args:
        file_path: Path to the file.
        root: Stop walking at this directory (exclusive). If None, walks to filesystem root.
        verbose: Print debug information about folder.yaml discovery.

    Returns:
        Merged FolderMetadata from all folder.yaml files in the path.
    """
    result = FolderMetadata()
    folder = file_path.parent

    # Collect all folder.yaml files from root to file (we'll reverse to apply in order)
    metadata_stack: list[tuple[Path, FolderMetadata]] = []

    if verbose:
        print(f"  [folder.yaml] Searching from: {folder}")
        if root:
            print(f"  [folder.yaml] Root boundary: {root}")

    while True:
        yaml_path = folder / "folder.yaml"
        if verbose:
            print(f"  [folder.yaml] Checking: {yaml_path} ... ", end="")

        metadata = load_folder_yaml(folder)
        if metadata:
            metadata_stack.append((folder, metadata))
            if verbose:
                print("FOUND")
                if metadata.date_range:
                    print(f"  [folder.yaml]   date: {metadata.date_range.not_earlier_than} to {metadata.date_range.not_later_than}")
                if metadata.place:
                    print(f"  [folder.yaml]   place: {metadata.place}")
        elif verbose:
            print("not found")

        if root and folder == root:
            if verbose:
                print(f"  [folder.yaml] Stopped at root boundary")
            break
        parent = folder.parent
        if parent == folder:  # Reached filesystem root
            if verbose:
                print(f"  [folder.yaml] Reached filesystem root")
            break
        folder = parent

    if verbose:
        print(f"  [folder.yaml] Found {len(metadata_stack)} folder.yaml file(s)")

    # Apply from root to leaf (so leaf overrides root)
    for folder, metadata in reversed(metadata_stack):
        # Merge date range
        if metadata.date_range:
            if result.date_range is None:
                result.date_range = DateRange()
            if metadata.date_range.not_earlier_than:
                result.date_range.not_earlier_than = metadata.date_range.not_earlier_than
                result.date_range.source_path = folder
            if metadata.date_range.not_later_than:
                result.date_range.not_later_than = metadata.date_range.not_later_than
                result.date_range.source_path = folder

        # Merge place (more specific overrides less specific)
        if metadata.place:
            if result.place is None:
                result.place = PlaceHint()
            if metadata.place.country:
                result.place.country = metadata.place.country
            if metadata.place.state:
                result.place.state = metadata.place.state
            if metadata.place.city:
                result.place.city = metadata.place.city
            if metadata.place.street:
                result.place.street = metadata.place.street
            if metadata.place.lat is not None:
                result.place.lat = metadata.place.lat
            if metadata.place.lon is not None:
                result.place.lon = metadata.place.lon

    if verbose:
        print(f"  [folder.yaml] Merged result: date={result.date_range}, place={result.place}")

    return result
