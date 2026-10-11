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


def project_utm_to_latlon(
    easting: float, northing: float, zone_number: int, northern: bool = True
) -> Tuple[float, float]:
    """Convert UTM projected coordinate to WGS84 geographic coordinate (longitude, latitude)."""
    lat, lon = utm.to_latlon(easting, northing, zone_number, northern=northern)
    return lon, lat


def project_webmercator_to_latlon(x: float, y: float) -> Tuple[float, float]:
    """Convert EPSG:3857 Web Mercator coordinate in meters to WGS84 geographic (longitude, latitude)."""
    lon = (x / 6378137.0) * (180.0 / math.pi)
    lat = (2.0 * math.atan(math.exp(y / 6378137.0)) - (math.pi / 2.0)) * (180.0 / math.pi)
    return lon, lat


def detect_and_normalize_crs(crs_string: Optional[str]) -> Tuple[str, bool]:
    """Inspect CRS identifier, returning standardized name and whether it is EPSG:4326.
    
    Returns:
        (normalized_crs_name, is_epsg_4326)
    """
    if not crs_string:
        return "UNKNOWN", False
    norm = crs_string.strip().upper()
    if "4326" in norm or norm in ("WGS84", "WGS 84", "OGC:CRS84", "CRS84", "EPSG:4326"):
        return "EPSG:4326 (WGS 84)", True
    if "3857" in norm or "900913" in norm:
        return "EPSG:3857 (Web Mercator)", False
    if "UTM" in norm or "326" in norm or "327" in norm:
        return norm, False
    return norm, False

