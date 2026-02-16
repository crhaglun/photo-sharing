"""Image processing: resizing and EXIF extraction."""

import io
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD, Base

# Register HEIC/HEIF support
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC support optional


@dataclass
class ExifData:
    """Extracted EXIF metadata."""

    camera_make: str | None = None
    camera_model: str | None = None
    lens: str | None = None
    focal_length: str | None = None
    aperture: str | None = None
    shutter_speed: str | None = None
    iso: int | None = None
    taken_at: datetime | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None
    raw_exif: dict | None = None


def resize_image(image: Image.Image, max_size: int, quality: int = 85) -> bytes:
    """Resize image to fit within max_size while preserving aspect ratio.

    Args:
        image: PIL Image to resize.
        max_size: Maximum dimension (width or height).
        quality: JPEG quality (1-100).

    Returns:
        JPEG bytes of resized image.
    """
    # Calculate new size preserving aspect ratio
    width, height = image.size
    if width > height:
        if width > max_size:
            new_width = max_size
            new_height = int(height * max_size / width)
        else:
            new_width, new_height = width, height
    else:
        if height > max_size:
            new_height = max_size
            new_width = int(width * max_size / height)
        else:
            new_width, new_height = width, height

    # Resize using high-quality resampling
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Convert to RGB if necessary (for JPEG output)
    if resized.mode in ("RGBA", "P"):
        resized = resized.convert("RGB")

    # Save to bytes
    buffer = io.BytesIO()
    resized.save(buffer, format="JPEG", quality=quality, optimize=True)
    return buffer.getvalue()


def create_thumbnail(image: Image.Image) -> bytes:
    """Create 100px square thumbnail with center crop. Prioritizes small file size.

    Args:
        image: PIL Image to create thumbnail from.

    Returns:
        JPEG bytes of 100x100 square thumbnail.
    """
    size = 100
    width, height = image.size

    # Calculate scaling to make shortest side = size
    scale = size / min(width, height)
    new_width = int(width * scale)
    new_height = int(height * scale)

    # Scale image
    scaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Calculate center crop coordinates
    left = (new_width - size) // 2
    top = (new_height - size) // 2

    # Crop to square
    thumbnail = scaled.crop((left, top, left + size, top + size))

    # Convert to RGB if necessary (for JPEG output)
    if thumbnail.mode in ("RGBA", "P"):
        thumbnail = thumbnail.convert("RGB")

    # Save to bytes
    buffer = io.BytesIO()
    thumbnail.save(buffer, format="JPEG", quality=60, optimize=True)
    return buffer.getvalue()


def create_default_view(image: Image.Image) -> bytes:
    """Create 2048px default view. Prioritizes quality."""
    return resize_image(image, max_size=2048, quality=92)


def _convert_to_degrees(value) -> float | None:
    """Convert EXIF GPS coordinates to decimal degrees."""
    try:
        d, m, s = value
        return float(d) + float(m) / 60 + float(s) / 3600
    except (TypeError, ValueError):
        return None


def _format_rational(value) -> str | None:
    """Format an EXIF rational value as a string."""
    try:
        if hasattr(value, "numerator") and hasattr(value, "denominator"):
            if value.denominator == 1:
                return str(value.numerator)
            return f"{value.numerator}/{value.denominator}"
        return str(value)
    except Exception:
        return None


def extract_exif(file_path: Path) -> ExifData:
    """Extract EXIF metadata from an image file.

    Tries modern getexif() API first (works with HEIC), then falls back
    to legacy _getexif() for older JPEG files if needed.

    Args:
        file_path: Path to the image file.

    Returns:
        ExifData with extracted metadata.
    """
    result = ExifData()
    raw_exif: dict = {}

    try:
        with Image.open(file_path) as img:
            decoded = {}
            gps_ifd = {}

            # Try modern getexif() API first (works with HEIC, modern JPEG)
            exif = img.getexif() if hasattr(img, 'getexif') else None
            if exif:
                # Get sub-IFDs for additional data
                exif_ifd = exif.get_ifd(IFD.Exif) if hasattr(IFD, 'Exif') else {}
                gps_ifd = exif.get_ifd(IFD.GPSInfo) if hasattr(IFD, 'GPSInfo') else {}

                # Build decoded EXIF dict from base EXIF
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    decoded[tag] = value

                # Add EXIF IFD data
                for tag_id, value in exif_ifd.items():
                    tag = TAGS.get(tag_id, tag_id)
                    decoded[tag] = value

            # Fallback to legacy _getexif() if modern API didn't find data
            if not decoded and hasattr(img, '_getexif'):
                legacy_exif = img._getexif()
                if legacy_exif:
                    for tag_id, value in legacy_exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        decoded[tag] = value

                    # Extract GPS from legacy format
                    if "GPSInfo" in decoded and isinstance(decoded["GPSInfo"], dict):
                        for tag_id, value in decoded["GPSInfo"].items():
                            tag = GPSTAGS.get(tag_id, tag_id)
                            gps_ifd[tag] = value

            if not decoded:
                return result

            # Extract common fields
            result.camera_make = decoded.get("Make")
            result.camera_model = decoded.get("Model")
            result.lens = decoded.get("LensModel")

            # Focal length
            if "FocalLength" in decoded:
                fl = decoded["FocalLength"]
                result.focal_length = f"{float(fl):.0f}mm" if fl else None

            # Aperture (FNumber)
            if "FNumber" in decoded:
                fn = decoded["FNumber"]
                result.aperture = f"f/{float(fn):.1f}" if fn else None

            # Shutter speed (ExposureTime)
            if "ExposureTime" in decoded:
                et = decoded["ExposureTime"]
                result.shutter_speed = _format_rational(et)
                if result.shutter_speed and float(et) < 1:
                    result.shutter_speed = f"1/{int(1/float(et))}"

            # ISO
            iso_val = decoded.get("ISOSpeedRatings") or decoded.get("PhotographicSensitivity")
            if iso_val:
                result.iso = int(iso_val) if iso_val else None

            # Date taken
            date_str = decoded.get("DateTimeOriginal") or decoded.get("DateTime")
            if date_str:
                try:
                    result.taken_at = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass

            # GPS coordinates - try numeric keys first (modern API), then string keys (legacy)
            if gps_ifd:
                lat_ref = gps_ifd.get(1) or gps_ifd.get("GPSLatitudeRef")
                lat = gps_ifd.get(2) or gps_ifd.get("GPSLatitude")
                lon_ref = gps_ifd.get(3) or gps_ifd.get("GPSLongitudeRef")
                lon = gps_ifd.get(4) or gps_ifd.get("GPSLongitude")

                if lat and lon:
                    result.gps_lat = _convert_to_degrees(lat)
                    result.gps_lon = _convert_to_degrees(lon)

                    if result.gps_lat and lat_ref == "S":
                        result.gps_lat = -result.gps_lat
                    if result.gps_lon and lon_ref == "W":
                        result.gps_lon = -result.gps_lon

            # Store sanitized raw EXIF (convert non-serializable values)
            for key, value in decoded.items():
                if key == "GPSInfo":
                    continue  # Skip binary GPS data
                try:
                    json.dumps(value)  # Test if serializable
                    raw_exif[key] = value
                except (TypeError, ValueError):
                    raw_exif[key] = str(value)

            result.raw_exif = raw_exif

    except Exception:
        # Return empty result if EXIF extraction fails
        pass

    return result


def get_image_dimensions(file_path: Path) -> tuple[int, int]:
    """Get image dimensions after applying EXIF orientation.

    Args:
        file_path: Path to the image file.

    Returns:
        Tuple of (width, height) in pixels.
    """
    with Image.open(file_path) as img:
        img = apply_exif_orientation(img)
        return img.size


def apply_exif_orientation(img: Image.Image) -> Image.Image:
    """Apply EXIF orientation to an image.

    Args:
        img: PIL Image (must have EXIF data accessible).

    Returns:
        Correctly oriented image.
    """
    try:
        exif = img.getexif()
        if exif:
            orientation = exif.get(274)  # Orientation tag (Base.Orientation)
            if orientation == 3:
                return img.rotate(180, expand=True)
            elif orientation == 6:
                return img.rotate(270, expand=True)
            elif orientation == 8:
                return img.rotate(90, expand=True)
    except Exception:
        pass
    return img


def load_image_with_orientation(file_path: Path) -> Image.Image:
    """Load an image and apply EXIF orientation.

    Args:
        file_path: Path to the image file.

    Returns:
        Correctly oriented PIL Image.
    """
    img = Image.open(file_path)
    return apply_exif_orientation(img)


def process_image(file_path: Path) -> tuple[bytes, bytes, ExifData]:
    """Process an image: create variants and extract EXIF.

    Args:
        file_path: Path to the original image.

    Returns:
        Tuple of (thumbnail_bytes, default_bytes, exif_data).
    """
    exif = extract_exif(file_path)

    with Image.open(file_path) as img:
        img = apply_exif_orientation(img)
        thumbnail = create_thumbnail(img)
        default = create_default_view(img)

    return thumbnail, default, exif
