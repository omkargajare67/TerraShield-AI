"""Interactive Folium map component for TerraShield AI."""

from typing import Any, Dict, List
import folium
from folium import GeoJsonTooltip, GeoJsonPopup


def get_parcel_style(feature: Dict[str, Any]) -> Dict[str, Any]:
    """Determine dynamic polygon style based on parcel status and leverage score."""
    props = feature.get("properties", {})
    is_excluded = props.get("is_excluded", False)
    rank = props.get("rank")
    leverage_score = props.get("demo_leverage_score")

    if is_excluded:
        return {
            "fillColor": "#a0aec0",  # Muted slate/gray
            "color": "#718096",
            "weight": 2,
            "dashArray": "5, 5",
            "fillOpacity": 0.45,
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
    center_coords: List[float] = [47.452, -121.780],
    zoom_start: int = 14,
) -> folium.Map:
    """Build an interactive Folium map rendering candidate and analyzed parcels.
    
    Includes distinct polygon styling, hover tooltips, and detailed click popups.
    """
    m = folium.Map(
        location=center_coords,
        zoom_start=zoom_start,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    features = geojson_data.get("features", [])
    if not features:
        return m

    # Extract all coordinate vertices to fit bounds automatically
    bounds_coords = []
    for feat in features:
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [])
        if coords and len(coords) > 0:
            for pt in coords[0]:
                bounds_coords.append([pt[1], pt[0]])  # Folium expects [lat, lon]

    # Create GeoJson layer with custom styling and popups
    def style_fn(feature):
        return get_parcel_style(feature)

    def highlight_fn(feature):
        return {
            "weight": 4,
            "color": "#1a365d",
            "fillOpacity": 0.85,
        }

    geojson_layer = folium.GeoJson(
        geojson_data,
        name="Candidate Parcels",
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=GeoJsonTooltip(
            fields=["parcel_id", "name", "is_excluded"],
            aliases=["Parcel ID:", "Name:", "Excluded:"],
            localize=True,
            sticky=True,
        ),
        popup=GeoJsonPopup(
            fields=[
                "parcel_id",
                "name",
                "area_hectares",
                "demo_baseline_risk",
                "demo_delta_risk",
                "demo_tree_count",
                "is_excluded",
            ],
            aliases=[
                "ID:",
                "Name:",
                "Area (ha):",
                "Baseline Risk:",
                "Modeled Δ Risk:",
                "Tree Count:",
                "Excluded:",
            ],
            localize=True,
            max_width=320,
        ),
    )

    geojson_layer.add_to(m)

    # Fit bounds if coordinates exist
    if bounds_coords:
        m.fit_bounds(bounds_coords)

    # Add legend
    legend_html = """
    <div style="position: fixed; 
                bottom: 25px; right: 25px; width: 220px; height: 145px; 
                background-color: white; border: 1px solid #cbd5e0; 
                border-radius: 6px; z-index:9999; font-size:12px;
                padding: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
      <b style="color: #1a202c;">Parcel Status Legend</b><br>
      <div style="margin-top:6px;">
        <span style="background: #2f855a; width: 14px; height: 14px; display: inline-block; vertical-align: middle; border: 1px solid #1c4532; margin-right: 6px;"></span> Rank 1 (Top Priority)<br>
        <span style="background: #48bb78; width: 14px; height: 14px; display: inline-block; vertical-align: middle; border: 1px solid #276749; margin-right: 6px;"></span> Eligible Candidate<br>
        <span style="background: #a0aec0; width: 14px; height: 14px; display: inline-block; vertical-align: middle; border: 1px dashed #718096; margin-right: 6px;"></span> Excluded Parcel<br>
        <span style="background: #68d391; width: 14px; height: 14px; display: inline-block; vertical-align: middle; border: 1px solid #2f855a; margin-right: 6px;"></span> Pre-Analysis Parcel
      </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m
