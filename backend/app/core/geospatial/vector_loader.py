"""Vector loading, geometry validation, and spatial intersection module."""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.validation import explain_validity

from backend.app.schemas.geospatial import (
    ParcelIntersectionResult,
    ProtectedAreaIntersectionResponse,
    VectorValidationResponse,
)


def load_and_validate_vector_file(
    file_path: Path,
) -> Tuple[List[Dict[str, Any]], VectorValidationResponse]:
    """Parse and validate a GeoJSON vector dataset.
    
    Validates structure, geometry validity with Shapely, and bounding box.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Vector file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as err:
            raise ValueError(f"Failed to parse vector JSON: {str(err)}")

    if data.get("type") != "FeatureCollection":
        raise ValueError("Root object must be a GeoJSON FeatureCollection.")

    features = data.get("features", [])
    if not features:
        raise ValueError("FeatureCollection contains no features.")

    validation_messages = []
    geom_types = set()
    valid_geoms = 0
    all_bounds = []

    for idx, feat in enumerate(features):
        geom_dict = feat.get("geometry")
        if not geom_dict:
            validation_messages.append(f"Feature index {idx} has missing geometry.")
            continue

        try:
            geom = shape(geom_dict)
            geom_types.add(geom.geom_type)
            if not geom.is_valid:
                validation_messages.append(
                    f"Feature {feat.get('id', idx)} geometry invalid: {explain_validity(geom)}"
                )
            else:
                valid_geoms += 1
            all_bounds.append(geom.bounds)  # (minx, miny, maxx, maxy)
        except Exception as exc:
            validation_messages.append(f"Feature index {idx} parsing error: {str(exc)}")

    # Overall bounding box
    if all_bounds:
        minx = min(b[0] for b in all_bounds)
        miny = min(b[1] for b in all_bounds)
        maxx = max(b[2] for b in all_bounds)
        maxy = max(b[3] for b in all_bounds)
    else:
        minx, miny, maxx, maxy = 0.0, 0.0, 0.0, 0.0

    crs_name = data.get("crs", {}).get("properties", {}).get("name", "EPSG:4326 (WGS 84)")
    is_valid = len(validation_messages) == 0

    val_response = VectorValidationResponse(
        format="GeoJSON",
        feature_count=len(features),
        crs=crs_name,
        geometry_types=list(geom_types),
        bounds={"minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy},
        is_valid=is_valid,
        validation_messages=validation_messages,
    )

    return features, val_response


def parse_uploaded_study_area(file_path: Path) -> Dict[str, Any]:
    """Parse, inspect CRS, reproject, and validate any supported vector format.
    
    Supports:
    - GeoJSON (.geojson, .json)
    - Zipped ESRI Shapefiles (.zip)
    - GeoPackage (.gpkg)
    - Shapefile (.shp)
    
    Returns standard GeoJSON FeatureCollection reprojected to EPSG:4326,
    bounds, centroid, area, and validation report.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Study area file not found: {file_path}")

    ext = file_path.suffix.lower()
    validation_messages: List[str] = []
    reprojected = False
    original_crs = "EPSG:4326 (WGS 84)"
    format_name = "GeoJSON"

    if ext in [".geojson", ".json"]:
        format_name = "GeoJSON"
        # Try GeoPandas for robust CRS & geometry handling
        try:
            import geopandas as gpd
            gdf = gpd.read_file(file_path)
            if gdf.crs is not None:
                original_crs = str(gdf.crs)
                if not gdf.crs.to_string().upper().endswith("4326"):
                    gdf = gdf.to_crs(epsg=4326)
                    reprojected = True
                    validation_messages.append(
                        f"Layer reprojected from source CRS '{original_crs}' to WGS 84 (EPSG:4326)."
                    )
            else:
                original_crs = "UNKNOWN (Unspecified)"
                # Check bounding coordinates
                total_b = gdf.total_bounds  # minx, miny, maxx, maxy
                if -180.0 <= total_b[0] and total_b[2] <= 180.0 and -90.0 <= total_b[1] and total_b[3] <= 90.0:
                    gdf = gdf.set_crs(epsg=4326)
                    validation_messages.append(
                        "CRS was unspecified; interpreted as WGS 84 (EPSG:4326) based on degree coordinate values."
                    )
                else:
                    raise ValueError(
                        f"Unspecified CRS with coordinates outside geographic [-180, 180, -90, 90] bounds: {total_b}"
                    )
            geojson_data = json.loads(gdf.to_json())
        except Exception as err:
            # Fallback to direct json parser
            with open(file_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)

    elif ext == ".zip":
        format_name = "ESRI Shapefile (ZIP)"
        try:
            import geopandas as gpd
            gdf = gpd.read_file(file_path)
            if gdf.crs is not None:
                original_crs = str(gdf.crs)
                if not gdf.crs.to_string().upper().endswith("4326"):
                    gdf = gdf.to_crs(epsg=4326)
                    reprojected = True
                    validation_messages.append(
                        f"Shapefile reprojected from source CRS '{original_crs}' to WGS 84 (EPSG:4326)."
                    )
            else:
                original_crs = "UNKNOWN (Missing .prj)"
                total_b = gdf.total_bounds
                if -180.0 <= total_b[0] and total_b[2] <= 180.0 and -90.0 <= total_b[1] and total_b[3] <= 90.0:
                    gdf = gdf.set_crs(epsg=4326)
                    validation_messages.append(
                        "Shapefile lacked .prj file; interpreted as WGS 84 (EPSG:4326) based on degree bounds."
                    )
                else:
                    raise ValueError(
                        f"Shapefile lacked .prj file and coordinates are outside geographic bounds: {total_b}. "
                        "Please include a valid .prj coordinate reference system in the ZIP archive."
                    )
            geojson_data = json.loads(gdf.to_json())
        except Exception as err:
            raise ValueError(f"Failed to read Shapefile ZIP archive: {str(err)}")

    elif ext in [".gpkg", ".shp"]:
        format_name = "OGC GeoPackage" if ext == ".gpkg" else "ESRI Shapefile"
        try:
            import geopandas as gpd
            gdf = gpd.read_file(file_path)
            if gdf.crs is not None:
                original_crs = str(gdf.crs)
                if not gdf.crs.to_string().upper().endswith("4326"):
                    gdf = gdf.to_crs(epsg=4326)
                    reprojected = True
                    validation_messages.append(
                        f"Layer reprojected from source CRS '{original_crs}' to WGS 84 (EPSG:4326)."
                    )
            else:
                original_crs = "UNKNOWN"
                total_b = gdf.total_bounds
                if -180.0 <= total_b[0] and total_b[2] <= 180.0 and -90.0 <= total_b[1] and total_b[3] <= 90.0:
                    gdf = gdf.set_crs(epsg=4326)
                    validation_messages.append(
                        "Layer lacked CRS metadata; interpreted as WGS 84 (EPSG:4326) based on degree bounds."
                    )
                else:
                    raise ValueError(f"Vector layer lacks CRS metadata: {total_b}")
            geojson_data = json.loads(gdf.to_json())
        except Exception as err:
            raise ValueError(f"Failed to read {format_name} layer: {str(err)}")
    else:
        raise ValueError(
            f"Unsupported vector file format '{ext}'. Supported formats: .geojson, .json, .zip (Shapefile archive), .gpkg (GeoPackage)."
        )

    features = geojson_data.get("features", [])
    if not features:
        raise ValueError(f"{format_name} contains zero features.")

    geom_types = set()
    all_bounds = []
    total_area_approx_ha = 0.0

    for idx, feat in enumerate(features):
        geom_dict = feat.get("geometry")
        if not geom_dict:
            validation_messages.append(f"Feature {idx} has missing geometry.")
            continue
        try:
            g = shape(geom_dict)
            geom_types.add(g.geom_type)
            if not g.is_valid:
                validation_messages.append(f"Feature {feat.get('id', idx)} geometry invalid: {explain_validity(g)}")
            all_bounds.append(g.bounds)
            # Area estimation (degrees to ha)
            # 1 deg^2 ~ 1.23e10 m^2 * cos(lat) => ha = m^2 / 10000
            mid_lat = (g.bounds[1] + g.bounds[3]) * 0.5
            import math
            cos_factor = math.cos(math.radians(mid_lat))
            deg2_to_ha = (111132.0 * 111132.0 * cos_factor) / 10000.0
            total_area_approx_ha += g.area * deg2_to_ha
        except Exception as exc:
            validation_messages.append(f"Feature {idx} geometry parsing error: {str(exc)}")

    if all_bounds:
        minx = min(b[0] for b in all_bounds)
        miny = min(b[1] for b in all_bounds)
        maxx = max(b[2] for b in all_bounds)
        maxy = max(b[3] for b in all_bounds)
    else:
        minx, miny, maxx, maxy = 0.0, 0.0, 0.0, 0.0

    centroid_lon = (minx + maxx) * 0.5
    centroid_lat = (miny + maxy) * 0.5

    return {
        "format": format_name,
        "original_crs": original_crs,
        "reprojected": reprojected,
        "feature_count": len(features),
        "geometry_types": list(geom_types),
        "bounds": {
            "minx": round(minx, 6),
            "miny": round(miny, 6),
            "maxx": round(maxx, 6),
            "maxy": round(maxy, 6),
        },
        "centroid": {"lon": round(centroid_lon, 6), "lat": round(centroid_lat, 6)},
        "area_approx_ha": round(total_area_approx_ha, 2),
        "geojson": geojson_data,
        "is_valid": len([m for m in validation_messages if "invalid" in m.lower()]) == 0,
        "validation_messages": validation_messages,
    }



def intersect_parcels_with_protected_areas(
    candidate_parcels_geojson: Dict[str, Any],
    protected_areas_features: List[Dict[str, Any]],
    protected_source_name: str = "World Database on Protected Areas (WDPA) Vector Layer",
) -> ProtectedAreaIntersectionResponse:
    """Perform spatial intersection tests between candidate parcels and protected-area boundaries.
    
    Preserves specific reserve names and legal reasons.
    """
    parcel_features = candidate_parcels_geojson.get("features", [])
    results: List[ParcelIntersectionResult] = []
    intersecting_count = 0

    # Build Shapely geometries for protected areas
    pa_records = []
    for pa_feat in protected_areas_features:
        try:
            pa_geom = shape(pa_feat.get("geometry", {}))
            props = pa_feat.get("properties", {})
            pa_name = props.get("name") or props.get("NAME") or props.get("DESIG") or "Designated Protected Reserve"
            pa_records.append({"geom": pa_geom, "name": pa_name, "props": props})
        except Exception:
            continue

    for p_feat in parcel_features:
        p_props = p_feat.get("properties", {})
        p_id = p_props.get("parcel_id", p_feat.get("id", "UNKNOWN"))
        p_name = p_props.get("name", "Unnamed Parcel")

        try:
            p_geom = shape(p_feat.get("geometry", {}))
        except Exception:
            results.append(
                ParcelIntersectionResult(
                    parcel_id=p_id,
                    name=p_name,
                    intersects_protected_area=False,
                    exclusion_recommended=False,
                    reason="Invalid parcel polygon geometry.",
                )
            )
            continue

        intersects = False
        intersecting_pa_names = []
        overlap_area_sqm = 0.0

        for pa in pa_records:
            if p_geom.intersects(pa["geom"]):
                intersects = True
                intersecting_pa_names.append(pa["name"])
                intersection_poly = p_geom.intersection(pa["geom"])
                # Approximate area: if coordinates in degrees, convert deg^2 to hectares (~1.1e10 m^2 / deg^2 near lat 47)
                overlap_area_sqm += intersection_poly.area

        if intersects:
            intersecting_count += 1
            # Rough conversion to hectares if in degrees:
            # At ~47.45N, 1 deg lon ~ 75,400m, 1 deg lat ~ 111,100m => 1 deg^2 ~ 8.37e9 m^2 = 837,000 ha
            overlap_ha = round(overlap_area_sqm * 837000.0, 2)
            results.append(
                ParcelIntersectionResult(
                    parcel_id=p_id,
                    name=p_name,
                    intersects_protected_area=True,
                    protected_area_names=intersecting_pa_names,
                    overlap_area_hectares=overlap_ha,
                    exclusion_recommended=True,
                    reason=(
                        f"Parcel intersects statutory reserve: {', '.join(intersecting_pa_names)}. "
                        "Planting excluded due to conservation restrictions."
                    ),
                )
            )
        else:
            results.append(
                ParcelIntersectionResult(
                    parcel_id=p_id,
                    name=p_name,
                    intersects_protected_area=False,
                    exclusion_recommended=False,
                    reason=None,
                )
            )

    return ProtectedAreaIntersectionResponse(
        status="completed",
        total_parcels_evaluated=len(parcel_features),
        intersecting_parcels_count=intersecting_count,
        results=results,
        protected_area_source=protected_source_name,
        disclaimer=(
            "Protected area exclusions are based on statutory vector intersection. "
            "Verified legal boundaries must be consulted before field interventions."
        ),
    )
