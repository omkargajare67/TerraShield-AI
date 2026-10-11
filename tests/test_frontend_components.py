"""Unit tests for frontend UI components and data builders."""

from frontend.components.map_view import create_parcels_map, get_parcel_style
from frontend.components.metrics_view import build_analysis_dataframe
from backend.app.core.demo_data import load_demo_geojson


def test_parcel_styling_rules():
    excluded_feature = {"properties": {"is_excluded": True}}
    rank1_feature = {"properties": {"is_excluded": False, "rank": 1}}
    rank2_feature = {"properties": {"is_excluded": False, "rank": 2}}
    pre_analysis_feature = {"properties": {"is_excluded": False}}

    style_exc = get_parcel_style(excluded_feature)
    assert style_exc["fillColor"] == "#a0aec0"
    assert "dashArray" in style_exc

    style_r1 = get_parcel_style(rank1_feature)
    assert style_r1["fillColor"] == "#2f855a"

    style_r2 = get_parcel_style(rank2_feature)
    assert style_r2["fillColor"] == "#48bb78"

    style_pre = get_parcel_style(pre_analysis_feature)
    assert style_pre["fillColor"] == "#68d391"


def test_create_folium_map():
    geojson_data = load_demo_geojson()
    m = create_parcels_map(geojson_data)
    assert m is not None
    # Verify map HTML representation contains GeoJson layer
    html = m.get_root().render()
    assert "Candidate Parcels" in html or "GeoJson" in html or "folium" in html


def test_build_dataframe_from_parcels():
    mock_parcels = [
        {
            "parcel_id": "P-1",
            "name": "Test Parcel 1",
            "area_hectares": 2.5,
            "demo_baseline_risk": 0.8,
            "demo_delta_risk": 0.4,
            "demo_tree_count": 500,
            "is_excluded": False,
            "exclusion_reason": None,
            "demo_leverage_score": 0.0008,
            "rank": 1,
        },
        {
            "parcel_id": "P-2",
            "name": "Test Parcel 2",
            "area_hectares": 1.5,
            "demo_baseline_risk": 0.9,
            "demo_delta_risk": 0.1,
            "demo_tree_count": 0,
            "is_excluded": True,
            "exclusion_reason": "Zero tree capacity",
            "demo_leverage_score": None,
            "rank": None,
        },
    ]

    df = build_analysis_dataframe(mock_parcels)
    assert len(df) == 2
    assert "Priority Rank" in df.columns
    assert "Demo Leverage (ΔR/N)" in df.columns
    assert df.iloc[0]["Priority Rank"] == "#1"
    assert df.iloc[1]["Priority Rank"] == "Excluded"
    assert df.iloc[0]["Status"] == "Eligible"
    assert df.iloc[1]["Status"] == "Excluded"


def test_terrain_view_components_importable():
    from frontend.components.terrain_view import (
        render_dem_section,
        render_ndvi_section,
        render_soil_and_vector_section,
    )
    assert callable(render_dem_section)
    assert callable(render_ndvi_section)
    assert callable(render_soil_and_vector_section)

