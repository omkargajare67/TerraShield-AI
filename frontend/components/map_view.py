"""Interactive Folium map component for TerraShield AI."""

from typing import Any, Dict, List
import folium
from folium import GeoJsonTooltip, GeoJsonPopup


def get_parcel_style(feature: Dict[str, Any]) -> Dict[str, Any]:
    """Determine dynamic polygon style based on parcel status, eligibility, and score."""
    props = feature.get("properties", {})
    eligibility = str(props.get("eligibility_status", "")).upper()
    is_excluded = props.get("is_excluded", False) or eligibility == "EXCLUDED"
    is_insufficient = eligibility == "INSUFFICIENT_DATA"
    rank = props.get("rank")

    if is_excluded:
        return {
            "fillColor": "#a0aec0",  # Muted slate/gray
            "color": "#718096",
            "weight": 2,
            "dashArray": "5, 5",
            "fillOpacity": 0.45,
        }

    if is_insufficient:
        return {
            "fillColor": "#f59e0b",  # Amber warning
            "color": "#b45309",
            "weight": 2,
            "dashArray": "3, 3",
            "fillOpacity": 0.40,
        }

    # If analyzed and ranked
    if rank == 1:
        return {
            "fillColor": "#2f855a",  # Vibrant forest green (highest priority)
            "color": "#1c4532",
            "weight": 3,
            "fillOpacity": 0.75,
        }
    elif rank is not None:
        return {
            "fillColor": "#48bb78",  # Medium leaf green
            "color": "#276749",
            "weight": 2,
            "fillOpacity": 0.60,
        }
    else:
        # Pre-analysis candidate state
        return {
            "fillColor": "#68d391",  # Light sage green
            "color": "#2f855a",
            "weight": 2,
            "fillOpacity": 0.50,
        }


def create_parcels_map(
    geojson_data: Dict[str, Any],
    boundary_geojson: Optional[Dict[str, Any]] = None,
    center_coords: Optional[List[float]] = None,
    zoom_start: int = 13,
) -> folium.Map:
    """Build an interactive Folium map rendering candidate and analyzed parcels.
    
    Includes distinct polygon styling, hover tooltips, detailed click popups,
    and optional study area boundary overlay.
    """
    features = geojson_data.get("features", [])
    bounds_coords = []

    # Calculate centroid from features
    for feat in features:
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if coords and len(coords) > 0:
            ring = coords[0] if geom.get("type") == "Polygon" else (coords[0][0] if coords[0] else [])
            for pt in ring:
                if len(pt) >= 2:
                    bounds_coords.append([pt[1], pt[0]])  # Folium expects [lat, lon]

    if not center_coords:
        if bounds_coords:
            center_lat = sum(c[0] for c in bounds_coords) / len(bounds_coords)
            center_lon = sum(c[1] for c in bounds_coords) / len(bounds_coords)
            center_coords = [center_lat, center_lon]
        else:
            center_coords = [11.60, 76.05]

    m = folium.Map(
        location=center_coords,
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
    )


    # 1. Add Study Area Boundary if provided
    if boundary_geojson and boundary_geojson.get("features"):
        folium.GeoJson(
            boundary_geojson,
            name="Study Area Boundary",
            style_function=lambda x: {
                "fillColor": "#3b82f6",
                "color": "#1d4ed8",
                "weight": 2.5,
                "fillOpacity": 0.08,
            },
            tooltip="Study Area Boundary",
        ).add_to(m)

    if not features:
        return m

    # Detect available fields in feature properties
    sample_props = features[0].get("properties", {})
    available_keys = set(sample_props.keys())

    # Build dynamic tooltip fields
    tooltip_fields = ["parcel_id"]
    tooltip_aliases = ["Parcel ID:"]
    if "rank" in available_keys:
        tooltip_fields.append("rank")
        tooltip_aliases.append("Rank:")
    if "priority_score_index" in available_keys:
        tooltip_fields.append("priority_score_index")
        tooltip_aliases.append("Score Index:")
    elif "demo_leverage_score" in available_keys:
        tooltip_fields.append("demo_leverage_score")
        tooltip_aliases.append("Leverage:")
    if "eligibility_status" in available_keys:
        tooltip_fields.append("eligibility_status")
        tooltip_aliases.append("Status:")
    elif "is_excluded" in available_keys:
        tooltip_fields.append("is_excluded")
        tooltip_aliases.append("Excluded:")
    if "primary_driver" in available_keys:
        tooltip_fields.append("primary_driver")
        tooltip_aliases.append("Driver:")

    # Build dynamic popup fields
    popup_fields = ["parcel_id"]
    popup_aliases = ["Parcel ID:"]
    for k, a in [
        ("rank", "Priority Rank:"),
        ("priority_score_index", "Priority Score:"),
        ("eligibility_status", "Eligibility:"),
        ("plantable_area_ha", "Plantable Area (ha):"),
        ("total_area_ha", "Total Area (ha):"),
        ("slope_mean_deg", "Mean Slope (°):"),
        ("fs_baseline_mean", "Baseline FS:"),
        ("fs_delta_mean", "Modeled ΔFS:"),
        ("primary_driver", "Primary Driver:"),
        ("estimated_required_stems", "Est. Stems:"),
        ("is_excluded", "Excluded:"),
    ]:
        if k in available_keys:
            popup_fields.append(k)
            popup_aliases.append(a)

    geojson_layer = folium.GeoJson(
        geojson_data,
        name="Candidate Planting Parcels",
        style_function=get_parcel_style,
        highlight_function=lambda x: {"weight": 3.5, "color": "#1e3a8a", "fillOpacity": 0.90},
        tooltip=GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True, sticky=True),
        popup=GeoJsonPopup(fields=popup_fields, aliases=popup_aliases, localize=True, max_width=320),
    )
    geojson_layer.add_to(m)

    # Fit bounds
    if bounds_coords:
        m.fit_bounds(bounds_coords)

    # Add interactive LayerControl
    folium.LayerControl(position="topright").add_to(m)

    # Add concise floating legend
    legend_html = """
    <div style="position: fixed; 
                bottom: 25px; right: 25px; width: 230px; 
                background-color: rgba(255, 255, 255, 0.95); border: 1px solid #cbd5e1; 
                border-radius: 8px; z-index:9999; font-size:11px; font-family: sans-serif;
                padding: 10px 14px; box-shadow: 0 4px 12px rgba(0,0,0,0.12);">
      <b style="color: #0f172a; font-size:12px;">TerraShield Parcel Status</b><br>
      <div style="margin-top:6px; line-height: 1.6;">
        <span style="background: #059669; width: 12px; height: 12px; display: inline-block; vertical-align: middle; border-radius: 2px; margin-right: 6px;"></span> <b>Rank 1 (Highest Priority)</b><br>
        <span style="background: #10b981; width: 12px; height: 12px; display: inline-block; vertical-align: middle; border-radius: 2px; margin-right: 6px;"></span> Top Priority (Ranks 2–5)<br>
        <span style="background: #34d399; width: 12px; height: 12px; display: inline-block; vertical-align: middle; border-radius: 2px; margin-right: 6px;"></span> Eligible Candidate<br>
        <span style="background: #64748b; width: 12px; height: 12px; display: inline-block; vertical-align: middle; border-radius: 2px; margin-right: 6px;"></span> Excluded (Slope/Reserve)<br>
        <span style="background: #f59e0b; width: 12px; height: 12px; display: inline-block; vertical-align: middle; border-radius: 2px; margin-right: 6px;"></span> Insufficient Data Coverage
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

