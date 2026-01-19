"""Reverse geocoding using Nominatim."""

import time
from dataclasses import dataclass

import click
import requests


@dataclass
class LocalizedName:
    """A name in multiple languages."""

    sv: str | None = None  # Swedish
    en: str | None = None  # English

    @property
    def best(self) -> str | None:
        """Return best available name (English preferred)."""
        return self.en or self.sv


@dataclass
class GeocodedPlace:
    """Result of reverse geocoding."""

    country: LocalizedName | None = None
    state: LocalizedName | None = None
    city: LocalizedName | None = None
    street: LocalizedName | None = None


class Geocoder:
    """Reverse geocoder using OpenStreetMap Nominatim."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

    # Nominatim usage policy: max 1 request per second
    MIN_REQUEST_INTERVAL = 1.0

    def __init__(self, user_agent: str = "photo-sharing-uploader/1.0"):
        """Initialize geocoder.

        Args:
            user_agent: User-Agent header for Nominatim requests (required by usage policy).
        """
        self.user_agent = user_agent
        self._last_request_time: float = 0
        self._cache: dict[tuple[float, float], GeocodedPlace | None] = {}

    def _rate_limit(self) -> None:
        """Ensure we don't exceed Nominatim's rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _round_coords(self, lat: float, lon: float, precision: int = 4) -> tuple[float, float]:
        """Round coordinates to reduce cache misses for nearby locations.

        4 decimal places = ~11m precision, good enough for street-level.
        """
        return (round(lat, precision), round(lon, precision))

    def reverse_geocode(self, lat: float, lon: float) -> GeocodedPlace | None:
        """Reverse geocode coordinates to a place.

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.

        Returns:
            GeocodedPlace with country/state/city/street, or None if failed.
        """
        # Round coordinates for cache efficiency
        cache_key = self._round_coords(lat, lon)

        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Rate limit
        self._rate_limit()

        try:
            response = requests.get(
                self.NOMINATIM_URL,
                params={
                    "lat": lat,
                    "lon": lon,
                    "format": "json",
                    "addressdetails": 1,
                    "namedetails": 1,  # Get names in multiple languages
                    "zoom": 18,  # Street-level detail
                    "accept-language": "en,sv",  # Prefer English, then Swedish
                },
                headers={"User-Agent": self.user_agent},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

        except (requests.RequestException, ValueError) as e:
            click.echo(f"    Nominatim error: {e}")
            self._cache[cache_key] = None
            return None

        if "address" not in data:
            print(f"    Nominatim: no address in response")
            self._cache[cache_key] = None
            return None

        addr = data["address"]
        names = data.get("namedetails", {})

        def localized(default: str | None) -> LocalizedName | None:
            """Create localized name from address and namedetails."""
            if not default:
                return None
            # namedetails contains name:en, name:sv etc for the primary result
            # For address components, we use the default (localized by accept-language)
            # and try to find alternatives in namedetails
            return LocalizedName(
                sv=default,  # Default comes from accept-language preference
                en=default,  # Same for now - Nominatim doesn't give per-component translations
            )

        # Extract place hierarchy
        # Nominatim returns different keys depending on location
        country = addr.get("country")
        state = addr.get("state") or addr.get("region") or addr.get("province")
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("municipality")
        )
        street = addr.get("road") or addr.get("street")

        result = GeocodedPlace(
            country=LocalizedName(sv=country, en=country) if country else None,
            state=LocalizedName(sv=state, en=state) if state else None,
            city=LocalizedName(sv=city, en=city) if city else None,
            street=LocalizedName(sv=street, en=street) if street else None,
        )

        city_name = result.city.en if result.city else None
        country_name = result.country.en if result.country else None
        click.echo(f"    Nominatim: {city_name or state}, {country_name}")
        self._cache[cache_key] = result
        return result


# Singleton instance for reuse across uploads
_geocoder: Geocoder | None = None


def get_geocoder() -> Geocoder:
    """Get or create the geocoder singleton."""
    global _geocoder
    if _geocoder is None:
        _geocoder = Geocoder()
    return _geocoder


def reverse_geocode(lat: float, lon: float) -> GeocodedPlace | None:
    """Reverse geocode coordinates using the singleton geocoder.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        GeocodedPlace with country/state/city/street, or None if failed.
    """
    return get_geocoder().reverse_geocode(lat, lon)
