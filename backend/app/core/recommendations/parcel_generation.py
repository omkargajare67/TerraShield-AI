"""Candidate parcel generation and grid discretization for spatial recommendation."""

from typing import Any, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field
from shapely.geometry import Polygon, mapping

from backend.app.core.recommendations.spatial_reference import (
    calculate_polygon_geodesic_area,
    meters_to_degrees,
)

DEFAULT_STUDY_BOUNDS: Dict[str, float] = {
    "min_lon": 76.00,
    "min_lat": 11.55,
    "max_lon": 76.10,
    "max_lat": 11.65,
}


class CandidateParcel(BaseModel):
    """Structured representation of a discretized candidate planning parcel."""
    parcel_id: str
    geometry: Dict[str, Any]
    bounds: Tuple[float, float, float, float] = Field(
        ..., description="(minx, miny, maxx, maxy)"
    )
    total_area_ha: float
    centroid: Tuple[float, float] = Field(
        ..., description="(lon, lat)"
    )
    grid_row: int
    grid_col: int
    is_edge_parcel: bool


def generate_candidate_parcels(
    min_lon: Optional[float] = None,
    min_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    cell_size_m: float = 300.0,
    bounds: Optional[Dict[str, float]] = None,
    cell_size_meters: Optional[float] = None,
    parcel_prefix: str = "PARCEL",
) -> List[CandidateParcel]:
    """Discretize the study area into candidate reforestation planning parcels.

    Respects WGS 84 ellipsoidal geometry, calculates exact geodesic parcel areas in hectares,
    and formats boundaries into valid GeoJSON polygons (RFC 7946, EPSG:4326).

    Args:
        min_lon: West bounding coordinate in degrees.
        min_lat: South bounding coordinate in degrees.
        max_lon: East bounding coordinate in degrees.
        max_lat: North bounding coordinate in degrees.
        cell_size_m: Target cell length and width in meters (default 300m).
        bounds: Optional dictionary {'min_lon', 'min_lat', 'max_lon', 'max_lat'}.
        cell_size_meters: Alias for cell_size_m.
        parcel_prefix: Prefix for deterministic parcel IDs.

    Returns:
        List of CandidateParcel objects.
    """
    effective_cell_size = cell_size_meters if cell_size_meters is not None else cell_size_m
    if effective_cell_size <= 0.0:
        raise ValueError(f"Cell size must be strictly positive (got {effective_cell_size} m).")

    if bounds is not None:
        b_min_lon = float(bounds.get("min_lon", bounds.get("minx", DEFAULT_STUDY_BOUNDS["min_lon"])))
        b_min_lat = float(bounds.get("min_lat", bounds.get("miny", DEFAULT_STUDY_BOUNDS["min_lat"])))
        b_max_lon = float(bounds.get("max_lon", bounds.get("maxx", DEFAULT_STUDY_BOUNDS["max_lon"])))
        b_max_lat = float(bounds.get("max_lat", bounds.get("maxy", DEFAULT_STUDY_BOUNDS["max_lat"])))
    else:
        b_min_lon = float(min_lon if min_lon is not None else DEFAULT_STUDY_BOUNDS["min_lon"])
        b_min_lat = float(min_lat if min_lat is not None else DEFAULT_STUDY_BOUNDS["min_lat"])
        b_max_lon = float(max_lon if max_lon is not None else DEFAULT_STUDY_BOUNDS["max_lon"])
        b_max_lat = float(max_lat if max_lat is not None else DEFAULT_STUDY_BOUNDS["max_lat"])

    if b_min_lon >= b_max_lon or b_min_lat >= b_max_lat:
        raise ValueError(f"Invalid bounding box: min coordinates must be strictly less than max ({b_min_lon}, {b_min_lat}, {b_max_lon}, {b_max_lat}).")

    mid_lat = (b_min_lat + b_max_lat) * 0.5
    dlon_deg, dlat_deg = meters_to_degrees(mid_lat, effective_cell_size, effective_cell_size)

    parcels: List[CandidateParcel] = []
    row_idx = 1
    lat_curr = b_max_lat  # North to South

    while lat_curr > b_min_lat:
        lat_south = max(b_min_lat, lat_curr - dlat_deg)
        col_idx = 1
        lon_curr = b_min_lon

        while lon_curr < b_max_lon:
            lon_east = min(b_max_lon, lon_curr + dlon_deg)

            # Build clockwise polygon ring: NW -> NE -> SE -> SW -> NW
            poly_coords = [
                [round(lon_curr, 7), round(lat_curr, 7)],
                [round(lon_east, 7), round(lat_curr, 7)],
                [round(lon_east, 7), round(lat_south, 7)],
                [round(lon_curr, 7), round(lat_south, 7)],
                [round(lon_curr, 7), round(lat_curr, 7)],
            ]

            area_ha = calculate_polygon_geodesic_area(poly_coords)
            c_lon = round((lon_curr + lon_east) * 0.5, 7)
            c_lat = round((lat_curr + lat_south) * 0.5, 7)
            parcel_id = f"{parcel_prefix}-R{row_idx:02d}-C{col_idx:02d}"

            is_edge = (
                abs(lon_east - b_max_lon) < 1e-9
                or abs(lat_south - b_min_lat) < 1e-9
                or abs(lon_curr - b_min_lon) < 1e-9
                or abs(lat_curr - b_max_lat) < 1e-9
            )

            geom_dict = {
                "type": "Polygon",
                "coordinates": [poly_coords],
            }

            parcels.append(
                CandidateParcel(
                    parcel_id=parcel_id,
                    geometry=geom_dict,
                    bounds=(round(lon_curr, 7), round(lat_south, 7), round(lon_east, 7), round(lat_curr, 7)),
                    total_area_ha=round(area_ha, 4),
                    centroid=(c_lon, c_lat),
                    grid_row=row_idx,
                    grid_col=col_idx,
                    is_edge_parcel=is_edge,
                )
            )

            lon_curr = lon_east
            col_idx += 1

        lat_curr = lat_south
        row_idx += 1

    return parcels


def generate_candidate_parcels_geojson(
    bounds: Optional[Dict[str, float]] = None,
    cell_size_meters: float = 300.0,
    parcel_prefix: str = "PARCEL",
) -> Dict[str, Any]:
    """Generate candidate parcels formatted as a GeoJSON FeatureCollection dictionary."""
    parcels = generate_candidate_parcels(
        bounds=bounds,
        cell_size_m=cell_size_meters,
        parcel_prefix=parcel_prefix,
    )
    features = []
    for p in parcels:
        features.append({
            "type": "Feature",
            "id": p.parcel_id,
            "geometry": p.geometry,
            "properties": {
                "parcel_id": p.parcel_id,
                "grid_row": p.grid_row,
                "grid_col": p.grid_col,
                "centroid_lon": p.centroid[0],
                "centroid_lat": p.centroid[1],
                "target_cell_size_m": cell_size_meters,
                "total_area_ha": p.total_area_ha,
                "is_edge_parcel": p.is_edge_parcel,
            },
        })

    return {
        "type": "FeatureCollection",
        "metadata": {
            "dataset_name": "TerraShield AI Candidate Planning Parcels",
            "crs": "EPSG:4326 (WGS 84)",
            "target_cell_size_m": cell_size_meters,
            "total_parcels": len(features),
            "total_area_ha": round(sum(p.total_area_ha for p in parcels), 2),
        },
        "features": features,
    }
