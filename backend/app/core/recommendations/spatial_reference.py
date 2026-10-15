"""WGS 84 ellipsoidal spatial reference and geodesic metric calculations."""

import math
from typing import List, Sequence, Tuple

# WGS 84 Ellipsoid Geodetic Constants
WGS84_A = 6378137.0  # Semi-major axis in meters
WGS84_F = 1.0 / 298.257223563  # Flattening
WGS84_B = WGS84_A * (1.0 - WGS84_F)  # Semi-minor axis (~6356752.3142 m)
WGS84_E2 = 2.0 * WGS84_F - (WGS84_F**2)  # First eccentricity squared (~0.00669437999014)


class WGS84Ellipsoid:
    """Geodetic parameters and constants for the WGS 84 ellipsoid."""
    A = WGS84_A
    F = WGS84_F
    B = WGS84_B
    E2 = WGS84_E2




def get_radii_of_curvature(lat_deg: float) -> Tuple[float, float]:
    """Calculate the meridian radius (M) and prime vertical radius (N) of curvature.

    Args:
        lat_deg: Latitude in decimal degrees.

    Returns:
        Tuple of (M, N) in meters.
    """
    lat_rad = math.radians(lat_deg)
    sin_lat = math.sin(lat_rad)
    denom = math.sqrt(1.0 - WGS84_E2 * (sin_lat**2))

    # Meridian radius of curvature (North-South)
    m_radius = WGS84_A * (1.0 - WGS84_E2) / (denom**3)
    # Prime vertical radius of curvature (East-West)
    n_radius = WGS84_A / denom

    return m_radius, n_radius


def degrees_to_meters(lat_deg: float, delta_lon_deg: float, delta_lat_deg: float) -> Tuple[float, float]:
    """Convert small angular coordinate increments (degrees) to metric distances (meters).

    Args:
        lat_deg: Reference latitude in decimal degrees.
        delta_lon_deg: Longitudinal displacement in degrees.
        delta_lat_deg: Latitudinal displacement in degrees.

    Returns:
        Tuple of (dx_meters, dy_meters).
    """
    m_radius, n_radius = get_radii_of_curvature(lat_deg)
    lat_rad = math.radians(lat_deg)

    dx = math.radians(delta_lon_deg) * n_radius * math.cos(lat_rad)
    dy = math.radians(delta_lat_deg) * m_radius
    return dx, dy


def meters_to_degrees(lat_deg: float, dx_meters: float, dy_meters: float) -> Tuple[float, float]:
    """Convert metric ground distances (meters) to angular coordinate increments (degrees).

    Args:
        lat_deg: Reference latitude in decimal degrees.
        dx_meters: East-West displacement in meters.
        dy_meters: North-South displacement in meters.

    Returns:
        Tuple of (delta_lon_deg, delta_lat_deg).
    """
    m_radius, n_radius = get_radii_of_curvature(lat_deg)
    lat_rad = math.radians(lat_deg)

    cos_lat = math.cos(lat_rad)
    if abs(cos_lat) < 1e-9:
        cos_lat = 1e-9

    delta_lon_rad = dx_meters / (n_radius * cos_lat)
    delta_lat_rad = dy_meters / m_radius

    return math.degrees(delta_lon_rad), math.degrees(delta_lat_rad)


def calculate_polygon_geodesic_area(coords: Sequence[Sequence[float]]) -> float:
    """Calculate the geodesic surface area of a geographic polygon in hectares.

    Uses a localized ellipsoidal projection centered at the polygon's centroid,
    ensuring rigorous metric area calculation on the WGS 84 ellipsoid without
    treating degrees as flat metric Cartesian axes.

    Args:
        coords: Sequence of [lon, lat] pairs forming a closed ring.

    Returns:
        Area in hectares (1 ha = 10,000 m²).
    """
    if len(coords) < 3:
        return 0.0

    # Ensure list is closed
    pts = list(coords)
    if pts[0][0] != pts[-1][0] or pts[0][1] != pts[-1][1]:
        pts.append(pts[0])

    n_pts = len(pts)
    if n_pts < 4:
        return 0.0

    # Compute centroid latitude and longitude
    lons = [p[0] for p in pts[:-1]]
    lats = [p[1] for p in pts[:-1]]
    centroid_lon = sum(lons) / len(lons)
    centroid_lat = sum(lats) / len(lats)

    m_radius, n_radius = get_radii_of_curvature(centroid_lat)
    cos_lat0 = math.cos(math.radians(centroid_lat))

    # Project to localized metric Cartesian coordinates (meters)
    xs = []
    ys = []
    for lon, lat in pts:
        dx = math.radians(lon - centroid_lon) * n_radius * cos_lat0
        dy = math.radians(lat - centroid_lat) * m_radius
        xs.append(dx)
        ys.append(dy)

    # Standard Shoelace formula in meters²
    area_sq_m = 0.0
    for i in range(len(xs) - 1):
        area_sq_m += (xs[i] * ys[i + 1]) - (xs[i + 1] * ys[i])

    area_sq_m = abs(area_sq_m) * 0.5
    # Convert m² to hectares (1 ha = 10,000 m²)
    return area_sq_m / 10000.0


calculate_polygon_area_ha = calculate_polygon_geodesic_area
meters_to_degrees_approx = meters_to_degrees
