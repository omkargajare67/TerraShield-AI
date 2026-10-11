"""Coordinate reference system validation and projection utilities."""

import math
from typing import Optional, Tuple
import utm


def is_geographic_crs(crs_string: Optional[str]) -> bool:
    """Determine if a given CRS string denotes geographic coordinates (lat/lon in degrees)."""
    if not crs_string:
        return False
    norm = crs_string.upper().strip()
    # Explicit projected checks
    if "UTM" in norm or "PROJECTED" in norm or "PROJCS" in norm:
        return False
    if "3857" in norm or "EPSG:326" in norm or "EPSG:327" in norm:
        return False
    return "4326" in norm or "GEOGCS" in norm or ("WGS 84" in norm and "ZONE" not in norm)


def get_meters_per_degree(latitude_deg: float) -> Tuple[float, float]:
    """Calculate the approximate metric distances for 1 degree of longitude and latitude.
    
    Uses standard WGS84 ellipsoidal geometry:
    - 1° latitude ≈ 111,132.95 - 559.82*cos(2*phi) + 1.175*cos(4*phi) meters
    - 1° longitude ≈ (pi/180) * a * cos(phi) / sqrt(1 - e^2 * sin^2(phi)) meters
    """
    phi = math.radians(latitude_deg)
    # WGS84 constants
    a = 6378137.0  # semi-major axis (meters)
    e_sq = 0.00669437999014  # first eccentricity squared

    # Meters per degree latitude
    meters_per_lat = (
        111132.954
        - 559.822 * math.cos(2 * phi)
        + 1.175 * math.cos(4 * phi)
    )

    # Meters per degree longitude
    meters_per_lon = (math.pi / 180.0) * a * math.cos(phi) / math.sqrt(1.0 - e_sq * (math.sin(phi) ** 2))
    return meters_per_lon, meters_per_lat


def project_latlon_to_utm(
    longitude: float, latitude: float
) -> Tuple[float, float, int, str]:
    """Convert WGS84 geographic coordinate to local UTM projection (easting, northing, zone, letter)."""
    easting, northing, zone_number, zone_letter = utm.from_latlon(latitude, longitude)
    return easting, northing, zone_number, zone_letter
