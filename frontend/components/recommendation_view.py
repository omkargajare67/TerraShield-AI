"""TerraShield AI - Phase 4 Spatial Recommendations UI Component.

Interactive controls for candidate parcel generation, zonal raster statistics,
rule-based eligibility, explainable prioritization, and artifact exports.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import folium
from folium import GeoJson, GeoJsonTooltip
import pandas as pd
import requests
import streamlit as st
from streamlit_folium import st_folium


def render_recommendation_tab(api_base_url: str):
    """Render the Spatial Recommendations engine interface."""
    st.subheader("🎯 Phase 4: Spatial Recommendation & Prioritization Engine")
    st.caption(
        "Multi-criteria spatial decision-support engine integrating verified Western Ghats terrain, "
        "Sentinel-2 vegetation index, and Phase 3 geotechnical slope stability modeling."
    )

    # 1. Scientific Integrity Notice
    st.markdown(
        """
        <div style="background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 0.9rem; border-radius: 6px; margin-bottom: 1.2rem; font-size: 0.9rem; color: #92400e;">
            <strong>⚠️ Scientific Integrity & Provenance Notice:</strong><br>
            • <strong>Genuine Observations:</strong> NASA SRTM NASADEM Global 1 Arc-Second V001 (NASADEM_HGT_n11e076) and Sentinel-2 10m NDVI (Wayanad pilot basin).<br>
            • <strong>Illustrative Scenario:</strong> Geotechnical Factor of Safety layers use user-supplied spatially uniform exploratory parameters.<br>
            • <strong>Leverage Metric Safeguard:</strong> Modeled ΔFS is a mechanical index, NOT empirical landslide risk reduction (ΔR). True leverage <em>L = ΔR / N</em> requires calibrated disaster probability curves.<br>
            • <strong>Protected Areas:</strong> Official cadastral reserve boundary layer unverified. Clearance remains pending local cadastral confirmation.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Fetch Backend Status
    try:
        status_res = requests.get(f"{api_base_url}/api/v1/recommendations/status", timeout=5)
        status_data = status_res.json() if status_res.status_code == 200 else {}
    except Exception:
        status_data = {}

    # Section A: Input Layer Availability
    with st.expander("📡 Input Layer & Dataset Status", expanded=False):
        col_s1, col_s2, col_s3 = st.columns(3)
        input_layers = status_data.get("input_layers", {})
        
        with col_s1:
            st.markdown("**Real Environmental Observations**")
            dem_ok = input_layers.get("dem", {}).get("available", False)
            ndvi_ok = input_layers.get("ndvi", {}).get("available", False)
            st.write(f"🏔️ DEM Elevation: {'✅ Available (NASA NASADEM 30m)' if dem_ok else '❌ Missing'}")
            st.write(f"🌿 Sentinel-2 NDVI: {'✅ Available (10m BOA)' if ndvi_ok else '❌ Missing'}")
            slope_ok = input_layers.get("slope", {}).get("available", False)
            st.write(f"📐 Slope Gradient: {'✅ Derived (30m Horn)' if slope_ok else '❌ Missing'}")

        with col_s2:
            st.markdown("**Phase 3 Geotechnical Models**")
            fs_b_ok = input_layers.get("fs_baseline", {}).get("available", False)
            fs_r_ok = input_layers.get("fs_reinforced", {}).get("available", False)
            c_req_ok = input_layers.get("required_cohesion", {}).get("available", False)
            st.write(f"📊 Baseline FS: {'⚠️ Available (Exploratory)' if fs_b_ok else '❌ Missing'}")
            st.write(f"🌳 Reinforced FS: {'⚠️ Available (Exploratory)' if fs_r_ok else '❌ Missing'}")
            st.write(f"🎯 Required Cohesion: {'⚠️ Available (Benchmark)' if c_req_ok else '❌ Missing'}")

        with col_s3:
            st.markdown("**Administrative & Silvicultural**")
            st.write("🛡️ Statutory Reserves: ⚠️ Unverified (No official cadastral shapefile)")
            st.write("🌱 Botanical Database: ℹ️ Pending Curated Evidence (Scientific integrity preserved)")
            st.caption(f"Study bounds: E 76.00°–76.10°, N 11.55°–11.65° | CRS: {status_data.get('native_crs', 'EPSG:4326')}")

    # Section B: Analysis Controls & Settings
    st.markdown("### ⚙️ Recommendation & Prioritization Parameters")
    c_grid, c_elig, c_weights = st.columns(3)

    with c_grid:
        st.markdown("**1. Spatial Discretization**")
        cell_size = st.select_slider(
            "Candidate Parcel Grid Resolution",
            options=[100, 200, 300, 500, 1000],
            value=300,
            help="Side length of candidate planning parcel in meters. Local ellipsoidal metric conversion.",
        )
        st.caption(f"Cell size {cell_size} m produces ~{(cell_size * cell_size) / 10000:.2f} ha nominal parcels.")

    with c_elig:
        st.markdown("**2. Eligibility & Exclusions**")
        max_slope = st.slider("Max Slope Gradient (°)", min_value=20.0, max_value=60.0, value=45.0, step=1.0)
        enable_canopy = st.checkbox("Enable NDVI Canopy Masking", value=False)
        canopy_thresh = 0.65
        if enable_canopy:
            canopy_thresh = st.slider("Dense Canopy Proxy Threshold (NDVI)", min_value=0.40, max_value=0.85, value=0.65, step=0.05)
        min_area_ha = st.number_input("Min Plantable Area (ha)", min_value=0.05, max_value=5.0, value=0.25, step=0.05)

    with c_weights:
        st.markdown("**3. Priority Score Weights**")
        w_need = st.slider("Geotechnical Need", min_value=0.0, max_value=1.0, value=0.35, step=0.05)
        w_gain = st.slider("Stability Gain (ΔFS)", min_value=0.0, max_value=1.0, value=0.30, step=0.05)
        w_area = st.slider("Plantable Acreage", min_value=0.0, max_value=1.0, value=0.20, step=0.05)
        w_conf = st.slider("Data Confidence", min_value=0.0, max_value=1.0, value=0.15, step=0.05)

    # Normalization Settings & Missing Data Policy Expander
    with st.expander("⚖️ Normalization Settings & Missing Data Policy", expanded=False):
        c_n1, c_n2, c_n3 = st.columns(3)
        with c_n1:
            max_delta_fs_ref = st.number_input(
                "Stability Gain Divisor (ΔFS ref)",
                value=15.0,
                min_value=1.0,
                max_value=50.0,
                step=1.0,
                help="Upper normalization reference for modeled Factor of Safety improvement.",
            )
        with c_n2:
            max_area_ref_ha = st.number_input(
                "Plantable Area Divisor (ha ref)",
                value=15.0,
                min_value=1.0,
                max_value=100.0,
                step=1.0,
                help="Upper normalization reference for plantable parcel acreage.",
            )
        with c_n3:
            missing_policy = st.selectbox(
                "Missing Data Policy",
                options=["RENORMALIZE_AVAILABLE", "ZERO_FILL", "BLOCK_UNAVAILABLE"],
                index=0,
                help="RENORMALIZE_AVAILABLE: Re-distributes weights across available components if an optional layer is missing.",
            )

    # Optional Budget Allocation Expander
    with st.expander("💰 Optional Silvicultural Budget Allocation", expanded=False):
        c_b1, c_b2, c_b3 = st.columns(3)
        with c_b1:
            total_budget = st.number_input("Total Available Budget (INR)", min_value=0.0, value=500000.0, step=50000.0)
        with c_b2:
            cost_per_sapling = st.number_input("Cost per Sapling (INR)", min_value=10.0, value=150.0, step=10.0)
        with c_b3:
            setup_cost = st.number_input("Fixed Parcel Setup Cost (INR)", min_value=0.0, value=5000.0, step=1000.0)
        enable_budget = total_budget > 0.0

    # Run Analysis Button
    col_btn, col_msg = st.columns([1, 3])
    with col_btn:
        run_clicked = st.button("🚀 Run Spatial Prioritization", use_container_width=True, type="primary")

    if run_clicked:
        with st.spinner("Executing spatial discretization, multi-raster zonal statistics, and explainable ranking..."):
            payload = {
                "cell_size_m": float(cell_size),
                "eligibility_settings": {
                    "min_terrain_coverage_pct": 80.0,
                    "max_slope_deg": float(max_slope),
                    "enable_ndvi_canopy_filter": enable_canopy,
                    "ndvi_canopy_threshold": float(canopy_thresh),
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
                    "max_delta_fs_ref": float(max_delta_fs_ref),
                    "max_area_ref_ha": float(max_area_ref_ha),
                },
                "missing_data_policy": missing_policy,
                "fs_target": 1.3,
            }
            if enable_budget:
                payload["budget_config"] = {
                    "total_budget_inr": float(total_budget),
                    "cost_per_sapling_inr": float(cost_per_sapling),
                    "fixed_parcel_setup_cost_inr": float(setup_cost),
                    "default_planting_density_stems_ha": 400.0,
                    "max_stems_per_ha_cap": 1000.0,
                }

            try:
                res = requests.post(f"{api_base_url}/api/v1/recommendations/run", json=payload, timeout=60)
                if res.status_code == 200:
                    st.session_state["phase4_recommendations"] = res.json()
                    st.success("Prioritization analysis completed successfully!")
                else:
                    st.error(f"Analysis failed ({res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Failed to communicate with recommendation engine: {str(e)}")

    # Display Results if available
    rec_data = st.session_state.get("phase4_recommendations")
    if not rec_data:
        st.info("💡 Configure parameters above and click **'Run Spatial Prioritization'** to evaluate candidate parcels.")
        return

    st.divider()

    # Section C: Metrics KPI Cards
    st.markdown("### 📊 Prioritization Summary")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total Parcels Evaluated", f"{rec_data.get('total_parcels', 0):,}")
    with kpi2:
        st.metric("Eligible for Planting", f"{rec_data.get('eligible_count', 0):,}")
    with kpi3:
        st.metric("Disqualified / Excluded", f"{rec_data.get('excluded_count', 0):,}")
    with kpi4:
        st.metric("Plantable Acreage", f"{rec_data.get('total_plantable_area_ha', 0.0):.1f} ha")

    # Policy and missing layers info
    policy_name = rec_data.get("applied_missing_data_policy", "RENORMALIZE_AVAILABLE")
    missing_layers = rec_data.get("missing_layers_detected", [])
    if missing_layers:
        st.info(f"ℹ️ **Missing Data Policy Applied ({policy_name}):** The following layers were absent: {', '.join(missing_layers)}. Active component weights were adjusted accordingly.")

    if not rec_data.get("is_discriminative", True):
        diff_warn = rec_data.get("differentiation_warning") or "Active scoring components are uniform across candidate parcels. Ranking suppressed to avoid false precision."
        st.warning(f"⚠️ {diff_warn}")

    # Budget summary if present
    b_sum = rec_data.get("budget_summary")
    if b_sum:
        st.markdown(
            f"""
            <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem; color: #166534;">
                <strong>💰 Budget Simulation Result:</strong> Funded <strong>{b_sum.get('parcels_funded_count', 0)}</strong> parcels 
                with <strong>{b_sum.get('total_stems_allocated', 0):,}</strong> saplings (₹{b_sum.get('total_budget_spent_inr', 0.0):,.0f} spent of ₹{b_sum.get('total_budget_inr', 0.0):,.0f}). Remaining: ₹{b_sum.get('remaining_budget_inr', 0.0):,.0f}.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Section D: Interactive Folium Map
    st.markdown("### 🗺️ Candidate Parcels & Priority Map")
    st.caption("Emerald: Top Ranked Eligible | Amber: Moderate Priority | Red: Disqualified | Gray: Insufficient Data")

    map_artifact = rec_data.get("artifacts", {}).get("parcels_geojson")
    if map_artifact:
        try:
            art_res = requests.get(f"{api_base_url}/api/v1/recommendations/artifacts/{map_artifact}", timeout=10)
            if art_res.status_code == 200:
                geojson_data = art_res.json()

                # Build Map centered on Wayanad pilot basin
                m = folium.Map(
                    location=[11.60, 76.05],
                    zoom_start=12,
                    tiles="CartoDB positron",
                )

                def style_fn(feature):
                    props = feature.get("properties", {})
                    status = props.get("eligibility_status")
                    rank = props.get("rank")
                    
                    if status == "EXCLUDED":
                        return {"fillColor": "#ef4444", "color": "#b91c1c", "weight": 1, "fillOpacity": 0.35}
                    elif status == "INSUFFICIENT_DATA":
                        return {"fillColor": "#9ca3af", "color": "#6b7280", "weight": 1, "fillOpacity": 0.25}
                    elif rank is not None and rank <= 10:
                        return {"fillColor": "#10b981", "color": "#047857", "weight": 2.5, "fillOpacity": 0.70}
                    elif rank is not None and rank <= 50:
                        return {"fillColor": "#3b82f6", "color": "#1d4ed8", "weight": 1.5, "fillOpacity": 0.50}
                    else:
                        return {"fillColor": "#eab308", "color": "#ca8a04", "weight": 1, "fillOpacity": 0.40}

                tooltip = GeoJsonTooltip(
                    fields=["parcel_id", "rank", "priority_score_index", "plantable_area_ha", "eligibility_status"],
                    aliases=["Parcel:", "Rank #:", "Priority Index:", "Plantable Area (ha):", "Status:"],
                    localize=True,
                )

                GeoJson(
                    geojson_data,
                    style_function=style_fn,
                    tooltip=tooltip,
                    name="Candidate Parcels",
                ).add_to(m)

                st_folium(m, width="100%", height=500, returned_objects=[])
        except Exception as e:
            st.warning(f"Could not render vector map overlay: {e}")

    # Section E: Top Ranked Parcels Table & Explainability
    st.markdown("### 🏆 Top Priority Candidate Parcels")
    top_recs = rec_data.get("top_recommendations", [])
    if top_recs:
        table_rows = []
        for r in top_recs:
            table_rows.append({
                "Rank": f"#{r.get('rank')}",
                "Parcel ID": r.get("parcel_id"),
                "Priority Score": f"{r.get('priority_score_index'):.1f}",
                "Plantable Area (ha)": f"{r.get('plantable_area_ha'):.2f}",
                "Total Area (ha)": f"{r.get('total_area_ha'):.2f}",
                "Mean Slope (°)": f"{r.get('slope_mean_deg') or 0.0:.1f}",
                "Baseline FS": f"{r.get('fs_baseline_mean') or 0.0:.2f}",
                "Modeled ΔFS": f"+{r.get('fs_delta_mean') or 0.0:.2f}",
                "Primary Driver": r.get("primary_driver", "N/A"),
            })
        df_top = pd.DataFrame(table_rows)
        st.dataframe(df_top, use_container_width=True, hide_index=True)

    # Section F: Parcel Inspection Deep Dive
    st.markdown("### 🔍 Parcel Detail & Explainability Audit")
    if top_recs:
        selected_pid = st.selectbox("Select Candidate Parcel to Inspect", [r.get("parcel_id") for r in top_recs])
        chosen = next((r for r in top_recs if r.get("parcel_id") == selected_pid), None)

        if chosen:
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                st.markdown(f"#### **{chosen.get('parcel_id')}** (Rank #{chosen.get('rank')})")
                st.markdown(f"**Priority Score Index:** `{chosen.get('priority_score_index'):.1f} / 100`")
                st.markdown(f"**Plantable Capacity:** `{chosen.get('plantable_area_ha')} ha` (Total: `{chosen.get('total_area_ha')} ha`)")
                st.markdown(f"**Primary Driver:** {chosen.get('primary_driver')}")
                if chosen.get("modeled_stability_gain_per_stem"):
                    st.markdown(f"**Modeled Stability Gain per Stem:** `{chosen.get('modeled_stability_gain_per_stem'):.6f} ΔFS/stem`")
                else:
                    st.caption("Leverage metric (ΔR/N) unavailable: requires calibrated risk curve.")

            with c_d2:
                st.markdown("**Environmental & Stability Context:**")
                st.write(f"• Mean Hillslope Gradient: {chosen.get('slope_mean_deg') or 'N/A'}°")
                st.write(f"• Baseline Factor of Safety: {chosen.get('fs_baseline_mean') or 'N/A'}")
                st.write(f"• Modeled Reinforcement Increment: +{chosen.get('fs_delta_mean') or 'N/A'} ΔFS")
                st.caption("Provenance: Phase 3 uniform parameter exploratory scenario.")

    # Section G: Downloadable Exports
    st.markdown("### 📥 Downloadable Analysis Products")
    st.caption("Generated directly from verified analysis runs. All products link traceable metadata.")
    
    col_dl1, col_dl2, col_dl3, col_dl4 = st.columns(4)
    artifacts = rec_data.get("artifacts", {})

    with col_dl1:
        geojson_file = artifacts.get("parcels_geojson")
        if geojson_file:
            st.link_button(
                "🗺️ Download GeoJSON",
                f"{api_base_url}/api/v1/recommendations/artifacts/{geojson_file}",
                use_container_width=True,
            )

    with col_dl2:
        metrics_csv = artifacts.get("parcel_metrics_csv")
        if metrics_csv:
            st.link_button(
                "📊 Download Metrics CSV",
                f"{api_base_url}/api/v1/recommendations/artifacts/{metrics_csv}",
                use_container_width=True,
            )

    with col_dl3:
        rankings_csv = artifacts.get("parcel_rankings_csv")
        if rankings_csv:
            st.link_button(
                "🏆 Download Rankings CSV",
                f"{api_base_url}/api/v1/recommendations/artifacts/{rankings_csv}",
                use_container_width=True,
            )

    with col_dl4:
        report_html = artifacts.get("audit_report_html")
        if report_html:
            st.link_button(
                "📑 View Audit Report (HTML)",
                f"{api_base_url}/api/v1/recommendations/artifacts/{report_html}",
                use_container_width=True,
            )
