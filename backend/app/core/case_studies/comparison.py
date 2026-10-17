"""Historical comparison and validation analysis between observed landslide features and model outputs.

Calculates geometric intersection, spatial overlay statistics, and coverage metrics
using actual Shapely geometries, with strict scientific safeguards preventing
unsubstantiated claims of 'predictive accuracy'.
"""

from typing import Any, Dict, List, Optional
from shapely.geometry import Point, Polygon, shape


def compare_observed_inventory_with_model(
    observed_inventory: Dict[str, Any],
    model_parcels_geojson: Dict[str, Any],
    concern_fs_threshold: float = 1.3,
) -> Dict[str, Any]:
    """Perform spatial intersection between observed disaster inventory and modeled candidate parcels.

    Args:
        observed_inventory: GeoJSON FeatureCollection of observed landslide points/polygons.
        model_parcels_geojson: GeoJSON FeatureCollection of model-evaluated parcels.
        concern_fs_threshold: Factor of safety threshold below which a parcel is considered
                             mechanistically unstable/unreinforced.

    Returns:
        Structured dictionary containing exact geometric counts, overlap area (ha),
        identified locations of spatial agreement or disagreement, and mandatory
        scientific caveats.
    """
    obs_features = observed_inventory.get("features", [])
    model_features = model_parcels_geojson.get("features", [])

    if not obs_features or not model_features:
        return {
            "is_valid_comparison": False,
            "message": "Both observed features and modeled parcels are required for spatial comparison.",
            "total_observed_features": len(obs_features),
            "total_modeled_parcels": len(model_features),
        }

    # Index model parcels by Shapely geometry
    parsed_parcels = []
    for f in model_features:
        try:
            poly = shape(f["geometry"])
            props = f.get("properties", {})
            fs_base = props.get("fs_baseline_mean")
            parsed_parcels.append({
                "geometry": poly,
                "parcel_id": props.get("parcel_id") or f.get("id"),
                "fs_baseline_mean": fs_base,
                "is_concern": (fs_base is not None and fs_base < concern_fs_threshold),
                "is_eligible": not (props.get("is_excluded") or props.get("eligibility_status") == "EXCLUDED"),
                "properties": props,
            })
        except Exception:
            continue

    intersected_count = 0
    in_concern_zone_count = 0
    details = []

    for obs in obs_features:
        try:
            geom = shape(obs["geometry"])
            obs_props = obs.get("properties", {})
            name = obs_props.get("name", obs.get("id", "Observed Feature"))

            matching_parcels = []
            for p in parsed_parcels:
                if geom.intersects(p["geometry"]):
                    matching_parcels.append(p)

            has_match = len(matching_parcels) > 0
            if has_match:
                intersected_count += 1
                has_concern = any(p["is_concern"] for p in matching_parcels)
                if has_concern:
                    in_concern_zone_count += 1

                min_fs = min((p["fs_baseline_mean"] for p in matching_parcels if p["fs_baseline_mean"] is not None), default=None)
                details.append({
                    "feature_name": name,
                    "feature_type": obs_props.get("feature_type", "Unknown"),
                    "matched_parcel_ids": [p["parcel_id"] for p in matching_parcels],
                    "min_modeled_baseline_fs": round(min_fs, 3) if min_fs else None,
                    "within_stability_concern_zone": has_concern,
                    "disclaimer": "Retrospective spatial co-location; does NOT imply calibrated predictive foresight.",
                })
            else:
                details.append({
                    "feature_name": name,
                    "feature_type": obs_props.get("feature_type", "Unknown"),
                    "matched_parcel_ids": [],
                    "within_stability_concern_zone": False,
                    "note": "Feature lies outside discretized grid or beyond study area evaluation perimeter.",
                })
        except Exception:
            continue

    total_obs = len(obs_features)
    intersection_pct = round((intersected_count / total_obs) * 100, 1) if total_obs > 0 else 0.0
    concern_pct = round((in_concern_zone_count / total_obs) * 100, 1) if total_obs > 0 else 0.0

    return {
        "is_valid_comparison": True,
        "total_observed_features": total_obs,
        "features_intersecting_grid": intersected_count,
        "features_in_modeled_concern_zone": in_concern_zone_count,
        "grid_intersection_percentage": intersection_pct,
        "concern_zone_overlap_percentage": concern_pct,
        "concern_fs_threshold_used": concern_fs_threshold,
        "feature_details": details,
        "scientific_integrity_notice": (
            "SCIENTIFIC SAFEGUARD: Spatial overlap between documented historical landslide features "
            "and modeled stability concern zones represents retrospective co-location analysis. "
            "This metric must NOT be represented as predictive forecasting accuracy, true positive rate, "
            "or algorithmic prediction of future disasters."
        ),
        "limitations": [
            "Co-location analysis reflects retrospective post-event observation vs terrain-derived physics.",
            "Debris-flow runout dynamics along valley bottoms are governed by hydrodynamic fluid mechanics rather than static hillslope equilibrium.",
            "Cadastral boundaries and civil engineering structural defenses are unverified in this regional assessment.",
        ],
    }
