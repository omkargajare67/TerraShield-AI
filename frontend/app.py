"""TerraShield AI - Environmental Intelligence Decision Support Dashboard.

Polished full-stack interface communicating with FastAPI backend for generalized
multi-criteria reforestation site prioritization, geospatial analysis, and geotechnical modeling.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium

# Add root directory to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from frontend.components.map_view import create_parcels_map

# Backend API Configuration
DEFAULT_API_URL = "http://127.0.0.1:8000"
API_BASE_URL = os.getenv("TERRASHIELD_API_URL", DEFAULT_API_URL).rstrip("/")

# Page Configuration
st.set_page_config(
    page_title="TerraShield AI | Geospatial Decision Support",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling (Deep Forest, Sage, Slate & Warm Off-White Theme)
st.markdown(
    """
    <style>
    :root {
        --primary-forest: #1c4532;
        --secondary-sage: #2f855a;
        --emerald-accent: #059669;
        --bg-warm: #f8fafc;
        --text-charcoal: #0f172a;
        --border-slate: #cbd5e1;
    }
    .main-header {
        color: #1c4532;
        font-size: 2.1rem;
        font-weight: 700;
        margin-bottom: 0.15rem;
        letter-spacing: -0.025em;
    }
    .sub-header {
        color: #475569;
        font-size: 1.0rem;
        margin-bottom: 1.0rem;
    }
    .badge-pill {
        display: inline-block;
        background-color: #ecfdf5;
        color: #065f46;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        border: 1px solid #a7f3d0;
        margin-bottom: 0.6rem;
    }
    .provenance-banner {
        background-color: #fffbeb;
        color: #92400e;
        border: 1px solid #fde68a;
        border-left: 4px solid #f59e0b;
        padding: 0.75rem 1.0rem;
        border-radius: 6px;
        font-size: 0.86rem;
        margin-bottom: 1.2rem;
        line-height: 1.45;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stButton>button {
        background-color: #2f855a;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        padding: 0.5rem 1.25rem;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1c4532;
        color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.15);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# API Helper Functions
def api_get(endpoint: str, timeout: float = 5.0) -> Optional[Any]:
    try:
        r = requests.get(f"{API_BASE_URL}{endpoint}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def api_post(endpoint: str, payload: Dict[str, Any], timeout: float = 60.0) -> Optional[Any]:
    try:
        r = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=timeout)
        if r.status_code == 200:
            return r.json()
        st.error(f"API Error ({r.status_code}): {r.text}")
    except Exception as e:
        st.error(f"Failed to communicate with backend: {str(e)}")
    return None


# Session State Initialization
if "selected_project_id" not in st.session_state:
    st.session_state["selected_project_id"] = "wayanad_pilot"
if "active_run_results" not in st.session_state:
    st.session_state["active_run_results"] = None
if "run_in_progress" not in st.session_state:
    st.session_state["run_in_progress"] = False


def main():
    # Header
    st.markdown('<span class="badge-pill">TerraShield AI v1.0 • Generalized Decision Support System</span>', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">🌲 TerraShield AI</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Multi-Criteria Geospatial & Geotechnical Reforestation Planning Dashboard</p>',
        unsafe_allow_html=True,
    )

    # Scientific Transparency Notice
    st.markdown(
        """
        <div class="provenance-banner">
            <strong>⚠️ Scientific Integrity & Operational Transparency:</strong> Limit-equilibrium infinite slope models 
            (Wu-Waldron root-cohesion formulation) provide mechanistic decision-support indices, not calibrated disaster probability forecasts 
            or certified engineering designs. Real observations (NASA SRTM 30m, Sentinel-2 10m) are verified; legal statutory reserve boundaries 
            require local cadastral verification.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Backend Health Check
    health = api_get("/health")

    # Fetch Projects List
    projects = api_get("/api/v1/projects") or []
    project_map = {p["id"]: p for p in projects}

    # Sidebar: Project Switcher & Controls
    with st.sidebar:
        st.header("🌐 Project Workspace")
        if health:
            st.success(f"Backend Connected ({health.get('mode', 'local').upper()})")
        else:
            st.error("Backend Disconnected")
            st.caption(f"Cannot reach `{API_BASE_URL}`. Start FastAPI backend with `scripts/start_backend.ps1`")

        st.divider()

        # Project Selector
        if projects:
            proj_options = [p["id"] for p in projects]
            proj_labels = {p["id"]: f"{'⭐ ' if p.get('is_builtin') else '📁 '}{p['name']}" for p in projects}

            current_id = st.session_state.get("selected_project_id", "wayanad_pilot")
            if current_id not in proj_options and proj_options:
                current_id = proj_options[0]

            selected_id = st.selectbox(
                "Active Project",
                options=proj_options,
                format_func=lambda x: proj_labels.get(x, x),
                index=proj_options.index(current_id) if current_id in proj_options else 0,
            )
            st.session_state["selected_project_id"] = selected_id
            active_proj = project_map.get(selected_id, {})
        else:
            st.warning("No projects loaded.")
            active_proj = {}

        # Quick Project Context Card
        if active_proj:
            st.caption(f"**Study Type:** `{active_proj.get('study_area_type', 'preset')}`")
            bounds = active_proj.get("bounds", {})
            st.caption(
                f"**Extents:** W {bounds.get('minx', 0):.2f}° – E {bounds.get('maxx', 0):.2f}° | "
                f"S {bounds.get('miny', 0):.2f}° – N {bounds.get('maxy', 0):.2f}°"
            )
            st.caption(f"**Native CRS:** `{active_proj.get('native_crs', 'EPSG:4326')}`")
            layers_count = len([k for k, v in active_proj.get("layers", {}).items() if v.get("path")])
            st.caption(f"**Available Layers:** {layers_count} layers attached")

        st.divider()

        # Quick Add New Project Modal / Expander
        with st.expander("➕ Create New Project", expanded=False):
            with st.form("new_project_form"):
                new_name = st.text_input("Project Name", placeholder="e.g. Idukki Ridge Corridor")
                new_desc = st.text_area("Description", placeholder="Watershed description and targets")
                new_preset = st.selectbox(
                    "Geotechnical Preset",
                    options=[
                        "wayanad_saprolite",
                        "colluvial_clay_silt",
                        "residual_sandy_loam",
                        "glacial_till_demo",
                    ],
                    format_func=lambda x: {
                        "wayanad_saprolite": "Tropical Monsoon Saprolite",
                        "colluvial_clay_silt": "Colluvial Clay-Silt",
                        "residual_sandy_loam": "Residual Sandy Loam",
                        "glacial_till_demo": "Glacial Till (Demo)",
                    }.get(x, x),
                )
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    new_minx = st.number_input("West Lon (minx)", value=76.00, format="%.4f")
                    new_miny = st.number_input("South Lat (miny)", value=11.55, format="%.4f")
                with col_b2:
                    new_maxx = st.number_input("East Lon (maxx)", value=76.10, format="%.4f")
                    new_maxy = st.number_input("North Lat (maxy)", value=11.65, format="%.4f")

                submit_new = st.form_submit_button("Create Project", use_container_width=True)
                if submit_new and new_name:
                    create_payload = {
                        "name": new_name,
                        "description": new_desc,
                        "study_area_type": "bbox",
                        "bounds": {"minx": new_minx, "miny": new_miny, "maxx": new_maxx, "maxy": new_maxy},
                        "geotech_preset_id": new_preset,
                    }
                    res = api_post("/api/v1/projects", create_payload)
                    if res:
                        st.session_state["selected_project_id"] = res["id"]
                        st.success(f"Created project '{res['name']}'!")
                        st.rerun()

    # Main Workflow Tabs
    tab_overview, tab_study, tab_data, tab_geotech, tab_prioritize, tab_results, tab_exports = st.tabs(
        [
            "🏠 Overview Dashboard",
            "🌐 1. Study Area Studio",
            "📁 2. Data & Raster Ingestion",
            "⚙️ 3. Geotechnical Studio",
            "🎯 4. Prioritization & Run",
            "📊 5. Results Explorer & Maps",
            "📥 6. Export Center & Provenance",
        ]
    )

    # TAB: Overview Dashboard
    with tab_overview:
        st.markdown(f"### Project Overview: **{active_proj.get('name', 'No Project Selected')}**")
        st.markdown(f"*{active_proj.get('description', 'No description provided.')}*")

        # Summary KPI Row
        c1, c2, c3, c4 = st.columns(4)
        bounds = active_proj.get("bounds", {})
        # Approx study area in hectares
        dlon = abs(bounds.get("maxx", 76.1) - bounds.get("minx", 76.0))
        dlat = abs(bounds.get("maxy", 11.65) - bounds.get("miny", 11.55))
        approx_ha = round(dlon * 111.0 * dlat * 111.0 * 100.0, 1)

        with c1:
            st.metric("Study Area Extent", f"~{approx_ha:,.0f} ha")
        with c2:
            st.metric("Study Area Type", active_proj.get("study_area_type", "Preset").title())
        with c3:
            saved_count = len(active_proj.get("saved_runs", []))
            st.metric("Saved Analysis Scenarios", f"{saved_count}")
        with c4:
            st.metric("CRS Status", "WGS 84 (EPSG:4326)")

        st.divider()

        # Guided Step Progress Banner
        st.markdown("#### 🚀 Analysis Workflow Steps")
        st.markdown(
            """
            Follow the guided tabs above to run end-to-end prioritization:
            1. **Study Area Studio:** Define boundary coordinates, upload GeoJSON/Shapefile/GeoPackage, or view preset extents.
            2. **Data & Raster Ingestion:** Upload custom DEM/NDVI GeoTIFFs, inspect spatial validity, and derive terrain layers.
            3. **Geotechnical Studio:** Calibrate soil and root cohesion parameters using standard physical presets.
            4. **Prioritization & Run:** Configure candidate parcel grid resolution, weights, eligibility rules, and launch analysis.
            5. **Results Explorer & Maps:** Inspect interactive Folium maps, parcel ranking breakdown, and parameter histograms.
            6. **Export Center & Provenance:** Download verified GeoJSON, CSV rankings, JSON summary, and HTML audit report.
            """
        )

        # Quick Start Actions
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🚀 Run Analysis on Current Project", use_container_width=True, type="primary"):
                st.session_state["run_in_progress"] = True
                with st.spinner("Executing end-to-end multi-criteria spatial analysis..."):
                    payload = {
                        "project_id": active_proj.get("id"),
                        "cell_size_m": active_proj.get("recommendation_settings", {}).get("cell_size_m", 300.0),
                    }
                    res = api_post("/api/v1/recommendations/run", payload)
                    if res:
                        st.session_state["active_run_results"] = res
                        st.success(f"Analysis completed successfully! Evaluated {res['total_parcels']} candidate parcels.")
                        st.rerun()

    # TAB 1: Study Area Studio
    with tab_study:
        st.markdown(f"### 🌐 Study Area Definition & Spatial Boundaries")
        st.caption("Inspect and configure geographic extents, CRS projections, and boundary geometries.")

        col_st1, col_st2 = st.columns([1, 1])
        with col_st1:
            st.markdown("#### 📐 Coordinate Extents & Boundary")
            with st.form("update_bounds_form"):
                b = active_proj.get("bounds", {"minx": 76.00, "miny": 11.55, "maxx": 76.10, "maxy": 11.65})
                u_minx = st.number_input("West Longitude (minx)", value=float(b.get("minx", 76.00)), format="%.4f")
                u_miny = st.number_input("South Latitude (miny)", value=float(b.get("miny", 11.55)), format="%.4f")
                u_maxx = st.number_input("East Longitude (maxx)", value=float(b.get("maxx", 76.10)), format="%.4f")
                u_maxy = st.number_input("North Latitude (maxy)", value=float(b.get("maxy", 11.65)), format="%.4f")

                up_btn = st.form_submit_button("Update Study Extents", use_container_width=True)
                if up_btn:
                    up_payload = {"bounds": {"minx": u_minx, "miny": u_miny, "maxx": u_maxx, "maxy": u_maxy}}
                    res = requests.put(f"{API_BASE_URL}/api/v1/projects/{active_proj.get('id')}", json=up_payload)
                    if res.status_code == 200:
                        st.success("Updated project bounding box!")
                        st.rerun()

            st.divider()
            st.markdown("#### 📤 Upload Vector Boundary or Exclusions")
            st.caption("Supported formats: `.geojson`, `.json`, `.zip` (ESRI Shapefile archive), `.gpkg` (GeoPackage).")
            vec_upload = st.file_uploader("Select Vector File", type=["geojson", "json", "zip", "gpkg"], key="study_vec_up")
            vec_purpose = st.radio("Vector Purpose", ["Study Area Boundary", "User Exclusions (Non-Plantable Areas)"], horizontal=True)

            if vec_upload and st.button("Ingest Vector Layer", use_container_width=True):
                purpose_code = "boundary" if "Boundary" in vec_purpose else "exclusion"
                files = {"file": (vec_upload.name, vec_upload.getvalue(), vec_upload.type)}
                data = {"purpose": purpose_code}
                try:
                    with st.spinner("Parsing geometries and inspecting CRS..."):
                        r = requests.post(f"{API_BASE_URL}/api/v1/projects/{active_proj.get('id')}/upload-vector", files=files, data=data)
                        if r.status_code == 200:
                            st.success("Successfully ingested and validated vector layer!")
                            st.json(r.json().get("report", {}).get("bounds", {}))
                            st.rerun()
                        else:
                            st.error(f"Upload failed: {r.text}")
                except Exception as e:
                    st.error(f"Upload error: {e}")

        with col_st2:
            st.markdown("#### 🗺️ Interactive Study Area Preview")
            b = active_proj.get("bounds", {"minx": 76.00, "miny": 11.55, "maxx": 76.10, "maxy": 11.65})
            c_lat = (b.get("miny", 11.55) + b.get("maxy", 11.65)) * 0.5
            c_lon = (b.get("minx", 76.00) + b.get("maxx", 76.10)) * 0.5

            # Construct boundary GeoJSON for display
            bbox_poly = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [b["minx"], b["miny"]],
                                [b["maxx"], b["miny"]],
                                [b["maxx"], b["maxy"]],
                                [b["minx"], b["maxy"]],
                                [b["minx"], b["miny"]],
                            ]],
                        },
                        "properties": {"name": active_proj.get("name", "Study Area")},
                    }
                ],
            }
            boundary_to_render = active_proj.get("boundary_geojson") or bbox_poly
            m_study = create_parcels_map(bbox_poly, boundary_geojson=boundary_to_render, center_coords=[c_lat, c_lon], zoom_start=12)
            st_folium(m_study, width="100%", height=450, returned_objects=[])

    # TAB 2: Data Layers & Ingestion
    with tab_data:
        st.markdown("### 📁 Data Layers & Raster Ingestion Studio")
        st.caption("Centralized management for elevation models (DEM), vegetation indices (NDVI), and derived terrain layers.")

        # Ingestion Controls
        col_up1, col_up2 = st.columns([1, 1])
        with col_up1:
            st.markdown("#### 📤 Upload GeoTIFF Raster Layer")
            raster_file = st.file_uploader("Select GeoTIFF Raster (.tif)", type=["tif", "tiff"], key="raster_up_ctrl")
            raster_type = st.selectbox("Layer Type", ["dem", "ndvi", "red", "nir"], format_func=lambda x: {
                "dem": "Elevation Model (DEM GeoTIFF)",
                "ndvi": "Vegetation Index (NDVI GeoTIFF)",
                "red": "Sentinel-2 Red Band (B04)",
                "nir": "Sentinel-2 Near-Infrared Band (B08)",
            }.get(x, x))

            if raster_file and st.button("Upload & Validate Raster", use_container_width=True):
                files = {"file": (raster_file.name, raster_file.getvalue(), "image/tiff")}
                data = {"layer_type": raster_type}
                try:
                    with st.spinner("Validating raster headers, NoData values, and spatial extent..."):
                        r = requests.post(f"{API_BASE_URL}/api/v1/projects/{active_proj.get('id')}/upload-raster", files=files, data=data)
                        if r.status_code == 200:
                            st.success(f"Successfully uploaded and validated {raster_type.upper()} GeoTIFF!")
                            st.json(r.json().get("validation", {}))
                            st.rerun()
                        else:
                            st.error(f"Raster upload failed: {r.text}")
                except Exception as e:
                    st.error(f"Error uploading raster: {e}")

        with col_up2:
            st.markdown("#### ⚡ Terrain & Geotechnical Derivation")
            st.caption("Derive slope and aspect rasters directly from the attached DEM.")
            has_dem = active_proj.get("layers", {}).get("dem", {}).get("path")
            if st.button("⚡ Process DEM into Slope & Aspect", use_container_width=True, disabled=not has_dem):
                with st.spinner("Calculating Horn 8-neighbourhood gradients and topographic aspect..."):
                    r = requests.post(f"{API_BASE_URL}/api/v1/projects/{active_proj.get('id')}/process-terrain")
                    if r.status_code == 200:
                        st.success("Terrain processing completed! Derived continuous slope and aspect rasters.")
                        st.rerun()
                    else:
                        st.error(f"Terrain derivation failed: {r.text}")

        st.divider()

        # Attached Layers Status Table
        st.markdown("#### 📊 Active Project Layer Inventory")
        layers = active_proj.get("layers", {})
        if layers:
            table_rows = []
            for k, info in layers.items():
                p_str = info.get("path", "")
                p_exists = Path(p_str).exists() if p_str else False
                table_rows.append({
                    "Layer Identifier": k.upper(),
                    "Status": "✅ Available" if p_exists else "❌ Missing / Unverified",
                    "Classification": info.get("status", "USER_LAYER"),
                    "File Name": Path(p_str).name if p_str else "N/A",
                    "Description": info.get("description", "Layer attached to workspace"),
                })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No layers currently attached to this project. Upload a DEM GeoTIFF above to begin.")

    # TAB 3: Geotechnical Studio
    with tab_geotech:
        st.markdown("### ⚙️ Geotechnical Calibration & Stability Studio")
        st.caption("Configure soil mechanical properties and Wu-Waldron root-reinforcement parameters.")

        gp = active_proj.get("geotechnical_parameters", {})
        soil = gp.get("soil", {})
        root = gp.get("root", {})

        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            st.markdown("#### 1. Soil Mechanical Properties")
            c_prime = st.number_input("Effective Cohesion c' (kPa)", value=float(soil.get("c_prime_kpa", 8.0)), min_value=0.5, max_value=50.0, step=0.5)
            phi_deg = st.number_input("Friction Angle φ' (°)", value=float(soil.get("phi_deg", 26.0)), min_value=5.0, max_value=45.0, step=1.0)
            gamma_kn = st.number_input("Unit Weight γ (kN/m³)", value=float(soil.get("gamma_kn_m3", 18.5)), min_value=10.0, max_value=25.0, step=0.5)
            depth_z = st.number_input("Regolith Depth z (m)", value=float(soil.get("depth_m", 1.8)), min_value=0.5, max_value=10.0, step=0.1)
            water_m = st.slider("Pore-Water Table Ratio m", min_value=0.0, max_value=1.0, value=float(soil.get("m_water_table", 0.5)), step=0.05, help="m=0.0 dry, m=1.0 fully saturated hillslope")

        with col_g2:
            st.markdown("#### 2. Root Reinforcement (Wu-Waldron)")
            t_r = st.number_input("Root Tensile Strength Tr (kPa)", value=float(root.get("tensile_stress_kpa", 25000.0)), min_value=5000.0, max_value=100000.0, step=2500.0)
            rar = st.number_input("Root Area Ratio (RAR)", value=float(root.get("rar", 0.002)), min_value=0.0001, max_value=0.02, step=0.0005, format="%.4f")
            k_factor = st.number_input("Wu-Waldron Empirical Factor k'", value=float(root.get("k_factor", 1.2)), min_value=1.0, max_value=1.4, step=0.05)
            target_fs = st.number_input("Target Safety Factor (FS target)", value=float(gp.get("target_fs", 1.3)), min_value=1.0, max_value=2.0, step=0.05)

        with col_g3:
            st.markdown("#### 3. Standard Presets & Persistence")
            chosen_preset = st.selectbox(
                "Load Physical Soil Preset",
                options=["Custom Engineering", "Tropical Monsoon Saprolite", "Colluvial Clay-Silt", "Residual Sandy Loam", "Glacial Till (Demo)"],
            )
            if st.button("Apply Selected Preset", use_container_width=True):
                preset_map = {
                    "Tropical Monsoon Saprolite": (8.0, 26.0, 18.5, 1.8, 0.5, 25000.0, 0.002, 1.2),
                    "Colluvial Clay-Silt": (12.0, 22.0, 19.0, 2.2, 0.6, 20000.0, 0.0015, 1.1),
                    "Residual Sandy Loam": (4.0, 32.0, 17.5, 1.5, 0.3, 30000.0, 0.0025, 1.2),
                    "Glacial Till (Demo)": (10.0, 28.0, 19.5, 1.6, 0.4, 22000.0, 0.0018, 1.15),
                }
                if chosen_preset in preset_map:
                    vals = preset_map[chosen_preset]
                    up_geotech = {
                        "geotechnical_parameters": {
                            "soil": {"c_prime_kpa": vals[0], "phi_deg": vals[1], "gamma_kn_m3": vals[2], "depth_m": vals[3], "m_water_table": vals[4]},
                            "root": {"tensile_stress_kpa": vals[5], "rar": vals[6], "k_factor": vals[7]},
                            "target_fs": 1.3,
                            "is_demo_parameters": "Demo" in chosen_preset,
                        }
                    }
                    requests.put(f"{API_BASE_URL}/api/v1/projects/{active_proj.get('id')}", json=up_geotech)
                    st.success(f"Applied preset '{chosen_preset}'!")
                    st.rerun()

            st.divider()
            # Action to generate geotechnical rasters
            has_slope = active_proj.get("layers", {}).get("slope", {}).get("path")
            if st.button("⚡ Generate Geotechnical Rasters", use_container_width=True, disabled=not has_slope):
                with st.spinner("Executing infinite slope stability modeling and root cohesion solvers..."):
                    r = requests.post(f"{API_BASE_URL}/api/v1/projects/{active_proj.get('id')}/process-geotechnical")
                    if r.status_code == 200:
                        st.success("Generated baseline FS, reinforced FS, and required cohesion rasters!")
                        st.rerun()
                    else:
                        st.error(f"Geotechnical analysis failed: {r.text}")

        # Interactive 1D Limit-Equilibrium Stability Simulator
        st.divider()
        st.markdown("#### 🔬 Real-Time Hillslope Stability Simulator (Limit-Equilibrium Equation)")
        sim_c1, sim_c2 = st.columns([1, 1])
        with sim_c1:
            slope_test_deg = st.slider("Hillslope Gradient (°)", min_value=5.0, max_value=55.0, value=30.0, step=1.0)
            beta_rad = np.radians(slope_test_deg)
            phi_rad = np.radians(phi_deg)
            gamma_w = 9.81  # kN/m^3

            # Baseline FS equation
            # FS0 = (c' + (gamma - m*gamma_w)*z*cos^2(beta)*tan(phi)) / (gamma*z*sin(beta)*cos(beta))
            denom = gamma_kn * depth_z * np.sin(beta_rad) * np.cos(beta_rad)
            num_base = c_prime + (gamma_kn - water_m * gamma_w) * depth_z * (np.cos(beta_rad) ** 2) * np.tan(phi_rad)
            fs_0 = max(0.0, num_base / denom) if denom > 0 else 999.0

            # Root cohesion increment
            delta_c = k_factor * t_r * rar
            num_reinf = (c_prime + delta_c) + (gamma_kn - water_m * gamma_w) * depth_z * (np.cos(beta_rad) ** 2) * np.tan(phi_rad)
            fs_reinf = max(0.0, num_reinf / denom) if denom > 0 else 999.0

            st.write(f"• Root Cohesion Increment: **+{delta_c:.2f} kPa**")
            st.write(f"• Baseline Factor of Safety ($FS_0$): **{fs_0:.2f}** {'(Unstable)' if fs_0 < 1.0 else '(Conditionally Stable)' if fs_0 < 1.3 else '(Stable)'}")
            st.write(f"• Root-Reinforced Factor of Safety ($FS_{{reinf}}$): **{fs_reinf:.2f}**")
            st.write(f"• Modeled Stability Improvement ($\\Delta FS$): **+{fs_reinf - fs_0:.2f}**")


        with sim_c2:
            # Curve plot across slopes
            slopes_range = np.linspace(10.0, 50.0, 41)
            b_rads = np.radians(slopes_range)
            d_arr = gamma_kn * depth_z * np.sin(b_rads) * np.cos(b_rads)
            fs0_arr = (c_prime + (gamma_kn - water_m * gamma_w) * depth_z * (np.cos(b_rads) ** 2) * np.tan(phi_rad)) / d_arr
            fsr_arr = ((c_prime + delta_c) + (gamma_kn - water_m * gamma_w) * depth_z * (np.cos(b_rads) ** 2) * np.tan(phi_rad)) / d_arr

            fig, ax = plt.subplots(figsize=(6, 3), dpi=100)
            ax.plot(slopes_range, fs0_arr, label="Baseline FS₀", color="#ef4444", lw=2)
            ax.plot(slopes_range, fsr_arr, label="Reinforced FS", color="#10b981", lw=2)
            ax.axhline(1.0, color="#64748b", ls="--", label="Limit Equilibrium (FS=1.0)")
            ax.axhline(target_fs, color="#f59e0b", ls=":", label=f"Target FS ({target_fs})")
            ax.set_ylim(0, 3.0)
            ax.set_xlabel("Slope Gradient (°)", fontsize=8)
            ax.set_ylabel("Factor of Safety", fontsize=8)
            ax.legend(fontsize=7)
            st.pyplot(fig)
            plt.close(fig)

    # TAB 4: Prioritization & Run
    with tab_prioritize:
        st.markdown("### 🎯 Multi-Criteria Prioritization Configuration")
        st.caption("Tune spatial grid resolution, multi-criteria weights, eligibility rules, and budget limits.")

        cp1, cp2, cp3 = st.columns(3)
        with cp1:
            st.markdown("#### 1. Spatial Discretization")
            cell_size = st.select_slider(
                "Candidate Parcel Grid Resolution (m)",
                options=[100, 200, 300, 500, 1000],
                value=300,
                help="Local ellipsoidal metric conversion for square parcel side length.",
            )
            st.caption(f"Produces parcels of ~{(cell_size * cell_size) / 10000.0:.2f} ha each.")

        with cp2:
            st.markdown("#### 2. Eligibility & Exclusions")
            max_slope_elig = st.slider("Max Slope Gradient (°)", 20.0, 60.0, 45.0, 1.0)
            enable_canopy_filt = st.checkbox("Enable NDVI Canopy Filter", value=False)
            canopy_th = 0.65
            if enable_canopy_filt:
                canopy_th = st.slider("Canopy Proxy Threshold (NDVI)", 0.40, 0.85, 0.65, 0.05)
            min_area_ha = st.number_input("Min Plantable Area (ha)", 0.05, 5.0, 0.25, 0.05)

        with cp3:
            st.markdown("#### 3. Component Weights")
            w_need = st.slider("Geotechnical Need", 0.0, 1.0, 0.35, 0.05)
            w_gain = st.slider("Stability Gain (ΔFS)", 0.0, 1.0, 0.30, 0.05)
            w_area = st.slider("Plantable Acreage", 0.0, 1.0, 0.20, 0.05)
            w_conf = st.slider("Data Confidence", 0.0, 1.0, 0.15, 0.05)

        # Advanced Settings & Budget Expander
        with st.expander("⚙️ Normalization References & Silvicultural Budget", expanded=False):
            cn1, cn2, cn3 = st.columns(3)
            with cn1:
                ref_delta_fs = st.number_input("Stability Gain Divisor (ΔFS ref)", 1.0, 50.0, 15.0, 1.0)
                ref_area_ha = st.number_input("Plantable Area Divisor (ha ref)", 1.0, 50.0, 15.0, 1.0)
            with cn2:
                missing_policy = st.selectbox("Missing Data Policy", ["RENORMALIZE_AVAILABLE", "ZERO_FILL", "BLOCK_UNAVAILABLE"])
            with cn3:
                budget_total = st.number_input("Total Planting Budget (INR)", 0.0, 10000000.0, 500000.0, 50000.0)
                cost_sapling = st.number_input("Cost per Sapling (INR)", 10.0, 500.0, 150.0, 10.0)

        st.divider()

        # Run Action Button
        col_run_act, col_run_info = st.columns([1, 2])
        with col_run_act:
            run_btn = st.button("🚀 Execute Prioritization Analysis", type="primary", use_container_width=True)

        if run_btn:
            with st.spinner("Extracting zonal statistics, evaluating eligibility, and computing priority rankings..."):
                payload = {
                    "project_id": active_proj.get("id"),
                    "cell_size_m": float(cell_size),
                    "eligibility_settings": {
                        "min_terrain_coverage_pct": 80.0,
                        "max_slope_deg": float(max_slope_elig),
                        "enable_ndvi_canopy_filter": enable_canopy_filt,
                        "ndvi_canopy_threshold": float(canopy_th),
                        "min_plantable_area_ha": float(min_area_ha),
                    },
                    "scoring_weights": {
                        "weight_geotechnical_need": float(w_need),
                        "weight_stability_gain": float(w_gain),
                        "weight_plantable_area": float(w_area),
                        "weight_data_confidence": float(w_conf),
                    },
                    "normalization_config": {
                        "fs_target": 1.3,
                        "critical_fs": 0.7,
                        "max_delta_fs_ref": float(ref_delta_fs),
                        "max_area_ref_ha": float(ref_area_ha),
                    },
                    "missing_data_policy": missing_policy,
                    "fs_target": 1.3,
                }
                if budget_total > 0.0:
                    payload["budget_config"] = {
                        "total_budget_inr": float(budget_total),
                        "cost_per_sapling_inr": float(cost_sapling),
                        "fixed_parcel_setup_cost_inr": 5000.0,
                        "default_planting_density_stems_ha": 400.0,
                        "max_stems_per_ha_cap": 1000.0,
                    }
                res = api_post("/api/v1/recommendations/run", payload)
                if res:
                    st.session_state["active_run_results"] = res
                    st.toast("Prioritization completed!", icon="✅")
                    st.success(f"Analysis completed successfully! Evaluated {res['total_parcels']} parcels.")
                    st.rerun()

    # TAB 5: Results Explorer & Maps
    with tab_results:
        st.markdown("### 📊 Geospatial Prioritization Results")
        results = st.session_state.get("active_run_results")

        if not results:
            st.info("💡 No analysis results in current session. Run an analysis from Step 4 or the Overview page.")
        else:
            # Summary Metrics Row
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("Total Parcels Evaluated", f"{results.get('total_parcels', 0):,}")
            with k2:
                st.metric("Eligible for Planting", f"{results.get('eligible_count', 0):,}")
            with k3:
                st.metric("Excluded (Slope / Excl.)", f"{results.get('excluded_count', 0):,}")
            with k4:
                st.metric("Total Plantable Capacity", f"{results.get('total_plantable_area_ha', 0.0):.1f} ha")

            if not results.get("is_discriminative", True):
                st.warning(f"⚠️ {results.get('differentiation_warning', 'Ranking suppressed due to uniform scoring inputs.')}")

            # Budget Card if applicable
            b_sum = results.get("budget_summary")
            if b_sum:
                st.success(
                    f"💰 **Budget Allocation Simulation:** Funded {b_sum.get('parcels_funded_count', 0)} parcels with "
                    f"{b_sum.get('total_stems_allocated', 0):,} saplings (Spent: ₹{b_sum.get('total_budget_spent_inr', 0):,.0f} of "
                    f"₹{b_sum.get('total_budget_inr', 0):,.0f}). Remaining: ₹{b_sum.get('remaining_budget_inr', 0):,.0f}."
                )

            st.divider()

            # Interactive Folium Map
            st.markdown("#### 🗺️ Interactive Candidate Parcels Map")
            art_id = results.get("artifacts", {}).get("parcels_geojson")
            if art_id:
                try:
                    geo_resp = requests.get(f"{API_BASE_URL}/api/v1/recommendations/artifacts/{art_id}", timeout=10)
                    if geo_resp.status_code == 200:
                        parcels_geo = geo_resp.json()
                        bound_geo = active_proj.get("boundary_geojson")
                        m_res = create_parcels_map(parcels_geo, boundary_geojson=bound_geo)
                        st_folium(m_res, width="100%", height=500, returned_objects=[])
                except Exception as e:
                    st.warning(f"Could not load map overlay: {e}")

            st.divider()

            # Rankings Table & Parcel Inspector
            col_tbl, col_insp = st.columns([1.4, 1.0])
            top_parcels = results.get("top_recommendations", [])

            with col_tbl:
                st.markdown("#### 🏆 Prioritized Parcel Recommendations")
                if top_parcels:
                    df_parcels = pd.DataFrame([
                        {
                            "Rank": f"#{p.get('rank')}",
                            "Parcel ID": p.get("parcel_id"),
                            "Score Index": f"{p.get('priority_score_index'):.1f}",
                            "Plantable (ha)": f"{p.get('plantable_area_ha'):.2f}",
                            "Mean Slope (°)": f"{p.get('slope_mean_deg') or 0.0:.1f}",
                            "Baseline FS": f"{p.get('fs_baseline_mean') or 0.0:.2f}",
                            "ΔFS Gain": f"+{p.get('fs_delta_mean') or 0.0:.2f}",
                            "Primary Driver": p.get("primary_driver", "N/A"),
                        }
                        for p in top_parcels
                    ])
                    st.dataframe(df_parcels, use_container_width=True, hide_index=True)

            with col_insp:
                st.markdown("#### 🔍 Explainable Parcel Inspector")
                if top_parcels:
                    inspect_pid = st.selectbox("Inspect Parcel", [p.get("parcel_id") for p in top_parcels])
                    chosen_p = next((p for p in top_parcels if p.get("parcel_id") == inspect_pid), None)
                    if chosen_p:
                        st.markdown(f"**Selected:** `{chosen_p.get('parcel_id')}` (Rank #{chosen_p.get('rank')})")
                        st.markdown(f"• **Priority Score:** `{chosen_p.get('priority_score_index'):.1f} / 100`")
                        st.markdown(f"• **Plantable Area:** `{chosen_p.get('plantable_area_ha')} ha`")
                        st.markdown(f"• **Primary Driver:** `{chosen_p.get('primary_driver')}`")
                        st.markdown(f"• **Hillslope Gradient:** `{chosen_p.get('slope_mean_deg') or 'N/A'}°`")
                        st.markdown(f"• **Baseline Factor of Safety:** `{chosen_p.get('fs_baseline_mean') or 'N/A'}`")
                        st.markdown(f"• **Modeled $\\Delta FS$ Improvement:** `+{chosen_p.get('fs_delta_mean') or 'N/A'}`")

                        if chosen_p.get("estimated_required_stems"):
                            st.markdown(f"• **Estimated Saplings Required:** `{int(chosen_p.get('estimated_required_stems')):,} stems`")

            # Parameter Distribution Histograms
            if top_parcels:
                st.divider()
                st.markdown("#### 📈 Parcel Characteristic Distributions")
                fig_h, (ax_s, ax_fs, ax_sc) = plt.subplots(1, 3, figsize=(12, 3), dpi=100)
                slopes = [p.get("slope_mean_deg") for p in top_parcels if p.get("slope_mean_deg") is not None]
                fss = [p.get("fs_baseline_mean") for p in top_parcels if p.get("fs_baseline_mean") is not None]
                scores = [p.get("priority_score_index") for p in top_parcels if p.get("priority_score_index") is not None]

                if slopes:
                    ax_s.hist(slopes, bins=10, color="#10b981", edgecolor="#047857")
                    ax_s.set_title("Mean Slope (°)", fontsize=9)
                if fss:
                    ax_fs.hist(fss, bins=10, color="#3b82f6", edgecolor="#1d4ed8")
                    ax_fs.set_title("Baseline FS", fontsize=9)
                if scores:
                    ax_sc.hist(scores, bins=10, color="#f59e0b", edgecolor="#b45309")
                    ax_sc.set_title("Priority Score Index", fontsize=9)

                st.pyplot(fig_h)
                plt.close(fig_h)

    # TAB 6: Export Center & Provenance
    with tab_exports:
        st.markdown("### 📥 Export Center & Scientific Provenance Disclosures")
        st.caption("Direct download links for verified spatial outputs, tabular metrics, and auditable documentation.")

        results = st.session_state.get("active_run_results")
        if not results:
            st.info("Run an analysis in Step 4 to generate exportable files.")
        else:
            artifacts = results.get("artifacts", {})
            st.markdown("#### 📂 Download Analysis Artifacts")
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)

            with col_a1:
                p_geo = artifacts.get("parcels_geojson")
                if p_geo:
                    st.link_button("🗺️ Download GeoJSON", f"{API_BASE_URL}/api/v1/recommendations/artifacts/{p_geo}", use_container_width=True)
            with col_a2:
                r_csv = artifacts.get("parcel_rankings_csv")
                if r_csv:
                    st.link_button("🏆 Download Rankings CSV", f"{API_BASE_URL}/api/v1/recommendations/artifacts/{r_csv}", use_container_width=True)
            with col_a3:
                m_csv = artifacts.get("parcel_metrics_csv")
                if m_csv:
                    st.link_button("📊 Download Metrics CSV", f"{API_BASE_URL}/api/v1/recommendations/artifacts/{m_csv}", use_container_width=True)
            with col_a4:
                rep_html = artifacts.get("audit_report_html")
                if rep_html:
                    st.link_button("📑 View Audit Report (HTML)", f"{API_BASE_URL}/api/v1/recommendations/artifacts/{rep_html}", use_container_width=True)

        st.divider()

        # Provenance Disclosures
        st.markdown("#### 🏷️ Data Provenance & Scientific Disclosures")
        st.markdown(
            f"""
            - **Elevation Data Provenance:** `{results.get('dem_source_provenance', 'NASA SRTM NASADEM Global 1 Arc-Second V001') if results else 'NASA SRTM NASADEM (Wayanad Watershed)'}`
            - **Verified SHA-256 Checksum (Wayanad NASADEM):** `680aa3cb46f4b7d148b2d62224ff8f8daa9591dcee5921d46c0f8c4c8a5ca2b6`
            - **Geotechnical Limit-Equilibrium Classification:** `ILLUSTRATIVE_SCENARIO` (uncalibrated parameter assumptions unless local borehole measurements supplied).
            - **Statutory Boundaries Status:** `UNVERIFIED` (Official legal cadastral reserve boundaries require local government validation).
            """
        )


if __name__ == "__main__":
    main()
