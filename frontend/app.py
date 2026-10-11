"""TerraShield AI - Phase 1 Foundation & Demonstration Interface.

Streamlit frontend communicating with FastAPI backend for geospatial
reforestation site prioritization demonstration.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import requests
import streamlit as st
from streamlit_folium import st_folium

# Add root directory to sys.path to enable local component imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from frontend.components.map_view import create_parcels_map
from frontend.components.metrics_view import (
    build_analysis_dataframe,
    render_metrics_cards,
    render_parcels_table,
)
from frontend.components.terrain_view import (
    render_dem_section,
    render_ndvi_section,
    render_soil_and_vector_section,
)
from frontend.components.geotechnical_view import render_geotechnical_tab
from frontend.components.recommendation_view import render_recommendation_tab

# Backend API Configuration
DEFAULT_API_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("TERRASHIELD_API_URL", DEFAULT_API_URL).rstrip("/")

# Page Configuration
st.set_page_config(
    page_title="TerraShield AI | Phase 1 Prototype",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Forest Green, Sage, and Neutral Theme)
st.markdown(
    """
    <style>
    :root {
        --primary-forest: #1c4532;
        --secondary-green: #2f855a;
        --light-sage: #f0f7f4;
        --accent-leaf: #38a169;
        --border-neutral: #e2e8f0;
    }
    .main-header {
        color: #1c4532;
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        letter-spacing: -0.02em;
    }
    .sub-header {
        color: #4a5568;
        font-size: 1.05rem;
        margin-bottom: 1.2rem;
    }
    .phase-badge {
        display: inline-block;
        background-color: #e6fffa;
        color: #234e52;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        border: 1px solid #b2f5ea;
        margin-bottom: 0.8rem;
    }
    .warning-banner {
        background-color: #fffaf0;
        color: #7b341e;
        border: 1px solid #fbd38d;
        border-left: 5px solid #dd6b20;
        padding: 0.85rem 1.1rem;
        border-radius: 6px;
        font-size: 0.88rem;
        margin-bottom: 1.2rem;
    }
    .info-card {
        background-color: #f7fafc;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #2f855a;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: background-color 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #276749;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def fetch_api_health() -> Optional[Dict[str, Any]]:
    """Check backend API health."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=3.0)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        return None
    return None


def fetch_candidate_parcels() -> Optional[Dict[str, Any]]:
    """Fetch demonstration candidate parcels GeoJSON from backend."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/parcels", timeout=5.0)
        if response.status_code == 200:
            return response.json()
        st.error(f"Backend error ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as exc:
        st.error(
            f"Unable to connect to backend at `{API_BASE_URL}`. "
            f"Please ensure the FastAPI backend is running.\n\nError: {exc}"
        )
    return None


def execute_analysis(scenario: str, min_risk: float) -> Optional[Dict[str, Any]]:
    """Send analysis execution request to backend."""
    payload = {"scenario": scenario, "min_risk_threshold": min_risk}
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/analysis", json=payload, timeout=8.0
        )
        if response.status_code == 200:
            return response.json()
        st.error(f"Analysis failed ({response.status_code}): {response.text}")
    except requests.exceptions.RequestException as exc:
        st.error(f"Analysis request failed to reach backend: {exc}")
    return None


def main():
    # Header & Identification
    st.markdown('<span class="phase-badge">Phase 1 Foundation & Working Prototype</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">TerraShield AI</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">AI-Assisted Reforestation Site Planning & Environmental Risk Analysis</p>',
        unsafe_allow_html=True,
    )

    # Required Warning Banner
    st.markdown(
        """
        <div class="warning-banner">
            <strong>⚠️ Phase 1 Demonstration Notice:</strong> Sample geometries and attributes are 
            illustrative and are not verified environmental observations. Results are not validated 
            geotechnical predictions or planting prescriptions.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar: System Status & Controls
    with st.sidebar:
        st.header("⚙️ System Status")
        health = fetch_api_health()
        if health:
            st.success(f"Backend Connected ({health.get('mode', 'demo').upper()} MODE)")
            st.caption(f"API Base URL: `{API_BASE_URL}`")
            st.caption(f"Backend Version: `v{health.get('version', '0.1.0')}`")
        else:
            st.error("Backend Disconnected")
            st.warning(
                f"Cannot reach `{API_BASE_URL}`. Please start the backend service:\n"
                "`python -m uvicorn backend.app.main:app --reload`"
            )

        st.divider()
        st.header("🎯 Analysis Parameters")

        scenario = st.selectbox(
            "Intervention Scenario",
            options=["landslide_mitigation", "urban_heat_mitigation (Planned Phase 3)", "air_quality_buffer (Planned Phase 4)"],
            index=0,
            help="Select the environmental risk intervention to evaluate.",
        )

        # Enforce validation and explain supported scenarios
        is_supported_scenario = scenario == "landslide_mitigation"
        if not is_supported_scenario:
            st.warning("⚠️ Only 'landslide_mitigation' is active in the Phase 1 demonstration pipeline.")

        min_risk = st.slider(
            "Min Baseline Risk Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            help="Filter out candidate parcels below this baseline risk index.",
        )

        st.caption("Prioritization Core Formula:")
        st.latex(r"L = \frac{\Delta R}{N}")
        st.caption("Leverage = Modeled Risk Reduction / Trees Required")

        st.divider()
        run_button = st.button("🚀 Run Demonstration Analysis", disabled=not is_supported_scenario or health is None)

    # Initialize Session State
    if "geojson_data" not in st.session_state:
        st.session_state["geojson_data"] = None
    if "analysis_results" not in st.session_state:
        st.session_state["analysis_results"] = None

    # Load initial candidate parcels if not already in session state
    if st.session_state["geojson_data"] is None and health is not None:
        with st.spinner("Fetching demonstration parcels from backend..."):
            parcels_data = fetch_candidate_parcels()
            if parcels_data:
                st.session_state["geojson_data"] = parcels_data

    # Execute analysis if triggered
    if run_button:
        with st.spinner("Executing deterministic leverage prioritization..."):
            results = execute_analysis("landslide_mitigation", min_risk)
            if results:
                st.session_state["analysis_results"] = results
                st.session_state["geojson_data"] = results.get("geojson")
                st.toast("Analysis completed successfully!", icon="✅")

    # Overview & Context Section
    with st.expander("📖 Project Overview & Phase 1 Scope", expanded=False):
        st.markdown(
            """
            ### Long-Term Purpose of TerraShield AI
            TerraShield AI is an AI-assisted geospatial decision-support system designed to identify
            promising reforestation locations and evaluate potential environmental benefits:
            1. **Landslide-risk mitigation** through strategically planned vegetative stabilization.
            2. **Air-quality improvement** through suitable vegetative buffers.
            3. **Urban-heat mitigation** through targeted urban canopy expansion.

            ### Central Prioritization Metric
            Candidate parcels are evaluated by their **Leverage Score**:
            $$L = \\frac{\\Delta R}{N}$$
            Where $\\Delta R$ denotes the calculated change in the defined risk metric, and $N$
            denotes the tree count associated with the intervention.

            ### Phase 1 Foundation Scope
            - Establishes the decoupled FastAPI backend and Streamlit frontend.
            - Operates on a deterministic, synthetic 5-parcel dataset in a sample watershed.
            - Evaluates statutory reserve and physical depth exclusions.
            - In subsequent phases, real satellite feeds (Copernicus Sentinel-2), elevation models (NASA SRTM),
              soil grids (ISRIC), and geotechnical root-cohesion solvers (Wu-Waldron) will be integrated.
            """
        )

    # Main Tabs Layout
    tab_map, tab_results, tab_recs, tab_geotech, tab_dem, tab_ndvi, tab_env, tab_study = st.tabs(
        [
            "🗺️ Interactive Map",
            "📊 Analysis Dashboard",
            "🎯 Spatial Recommendations",
            "📐 Geotechnical Intelligence",
            "🏔️ DEM & Terrain",
            "🌿 Sentinel-2 NDVI",
            "🛡️ Environmental Constraints",
            "📍 Study Area Details",
        ]
    )

    # Tab 1: Interactive Map
    with tab_map:
        st.markdown("### Illustrative Study Area Map")
        st.caption(
            "Displaying candidate parcels from backend. Click any parcel polygon to view attributes. "
            "Hover to view identifiers and exclusion status."
        )

        current_geojson = st.session_state.get("geojson_data")
        if current_geojson:
            parcels_map = create_parcels_map(current_geojson)
            st_folium(parcels_map, width="100%", height=520, returned_objects=[])
        else:
            st.info("Parcels data is loading or backend is currently unavailable. Please verify API connection.")

    # Tab 2: Results Dashboard
    with tab_results:
        results_data = st.session_state.get("analysis_results")
        if results_data:
            st.markdown("### Demonstration Analysis Results")
            render_metrics_cards(results_data)
            st.divider()

            parcels_list = results_data.get("parcels", [])
            render_parcels_table(parcels_list)

            st.divider()
            st.subheader("📥 Data Export & Downloads")
            st.caption("Download the generated analysis results directly in GeoJSON or tabular CSV format.")

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                geojson_str = json.dumps(results_data.get("geojson", {}), indent=2)
                st.download_button(
                    label="📄 Download Results GeoJSON",
                    data=geojson_str,
                    file_name="terrashield_analysis_results.geojson",
                    mime="application/geo+json",
                    use_container_width=True,
                )

            with col_dl2:
                df = build_analysis_dataframe(parcels_list)
                csv_str = df.to_csv(index=False)
                st.download_button(
                    label="📊 Download Results CSV",
                    data=csv_str,
                    file_name="terrashield_analysis_results.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
        else:
            st.info(
                "💡 No analysis has been executed yet. Click **'Run Demonstration Analysis'** "
                "in the sidebar to calculate deterministic leverage scores and parcel rankings."
            )

    # Tab 3: Spatial Recommendations Engine (Phase 4)
    with tab_recs:
        render_recommendation_tab(API_BASE_URL)

    # Tab 4: Geotechnical Intelligence Engine (Phase 3)
    with tab_geotech:
        render_geotechnical_tab(API_BASE_URL)

    # Tab 4: DEM & Terrain Analysis (Phase 2)
    with tab_dem:
        render_dem_section(API_BASE_URL)

    # Tab 4: Sentinel-2 NDVI Analysis (Phase 2)
    with tab_ndvi:
        render_ndvi_section(API_BASE_URL)

    # Tab 5: Environmental Constraints & Soil (Phase 2)
    with tab_env:
        render_soil_and_vector_section(API_BASE_URL)

    # Tab 6: Study Area Details & Pilot Corridor
    with tab_study:
        st.markdown("### 📍 Intended Project Pilot Corridor: Western Ghats")
        st.markdown(
            """
            TerraShield AI is designed for real-world deployment in the **Western Ghats Mountain Corridor (India)**,
            an internationally recognized biodiversity hotspot that experiences severe monsoon-triggered shallow landslides
            and steep-slope soil loss.

            - **Intended Pilot Region:** Western Ghats Corridor (Kerala, Tamil Nadu, Karnataka)
            - **Geographic Bounding Box:** `9.20° N – 12.00° N`, `75.80° E – 77.50° E`
            - **Recommended Projected CRS:** `EPSG:32643 (WGS 84 / UTM Zone 43N)`
            - **Target Environmental Risks:** Steep-slope debris flows, rainfall-induced shallow slips, and agricultural buffer loss.
            """
        )
        st.divider()
        st.markdown("### 🧪 Synthetic Test Fixtures (Cascade Foothills Demo)")
        st.markdown(
            """
            The built-in sample parcel dataset and test rasters use the **Cascade Foothills Demonstration Basin**:
            - **Nature:** 100% deterministic synthetic geometries and attributes generated for automated test suites.
            - **Coordinates:** Centered at `47.452° N, -121.780° W` (`EPSG:4326`).
            - **Notice:** This synthetic data must not be confused with real environmental observations in the Western Ghats.
            """
        )
        st.divider()
        st.markdown("### 🏷️ TerraShield AI Three-Tier Data Provenance Model")
        st.markdown(
            """
            1. **Synthetic Test Data:** Deterministic offline fixtures for code validation without external network dependencies.
            2. **Real Environmental Observations:** Genuine satellite (Sentinel-2 L2A), elevation (SRTM/LiDAR), soil (ISRIC), and reserve (WDPA) inputs uploaded or supplied by users.
            3. **Derived Geospatial Products:** Continuous Slope, Aspect, and NDVI continuous rasters computed deterministically from verified inputs.
            """
        )

    # Footer Notice
    st.divider()
    st.caption(
        "TerraShield AI Phase 1 Prototype | Designed for clean extensibility into geotechnical, "
        "raster, and machine-learning modules in Phases 2-5."
    )


if __name__ == "__main__":
    main()
