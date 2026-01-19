"""Image processing: resizing and EXIF extraction."""

import io
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS


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
    """Create 100px thumbnail. Prioritizes small file size."""
    return resize_image(image, max_size=100, quality=60)


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

    Args:
        file_path: Path to the image file.

    Returns:
        ExifData with extracted metadata.
    """
    result = ExifData()
    raw_exif: dict = {}

    try:
        with Image.open(file_path) as img:
            exif = img._getexif()
            if not exif:
                return result

            # Build decoded EXIF dict
            decoded = {}
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                decoded[tag] = value

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
            if "ISOSpeedRatings" in decoded:
                iso = decoded["ISOSpeedRatings"]
                result.iso = int(iso) if iso else None

            # Date taken
            date_str = decoded.get("DateTimeOriginal") or decoded.get("DateTime")
            if date_str:
                try:
                    result.taken_at = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass

            # GPS coordinates
            gps_info = decoded.get("GPSInfo")
            if gps_info:
                gps_decoded = {}
                for tag_id, value in gps_info.items():
                    tag = GPSTAGS.get(tag_id, tag_id)
                    gps_decoded[tag] = value

                lat = gps_decoded.get("GPSLatitude")
                lat_ref = gps_decoded.get("GPSLatitudeRef")
                lon = gps_decoded.get("GPSLongitude")
                lon_ref = gps_decoded.get("GPSLongitudeRef")

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


def process_image(file_path: Path) -> tuple[bytes, bytes, ExifData]:
    """Process an image: create variants and extract EXIF.

    Args:
        file_path: Path to the original image.

    Returns:
        Tuple of (thumbnail_bytes, default_bytes, exif_data).
    """
    exif = extract_exif(file_path)

    with Image.open(file_path) as img:
        # Handle EXIF orientation
        try:
            exif_data = img._getexif()
            if exif_data:
                orientation = exif_data.get(274)  # Orientation tag
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        except Exception:
            pass

        thumbnail = create_thumbnail(img)
        default = create_default_view(img)

    return thumbnail, default, exif
