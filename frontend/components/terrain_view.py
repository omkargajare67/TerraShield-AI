"""Streamlit UI components for Phase 2 Geospatial Terrain, NDVI, Soil, and Vector analysis."""

from typing import Any, Dict, Optional
import pandas as pd
import requests
import streamlit as st


def render_dem_section(api_base_url: str) -> None:
    """Render the DEM inspection, terrain analysis, and visualization UI."""
    st.markdown("### 🏔️ Digital Elevation Model (DEM) & Terrain Analysis")
    st.markdown(
        "Upload a validated GeoTIFF elevation raster to calculate elevation statistics, "
        "finite-difference slope (in degrees), and terrain aspect (azimuth from North)."
    )

    col_up1, col_up2 = st.columns([2, 1])
    with col_up1:
        dem_file = st.file_uploader(
            "Select DEM GeoTIFF Raster (.tif, .tiff)",
            type=["tif", "tiff"],
            key="dem_uploader",
            help="Accepts GeoTIFF rasters with valid georeferencing and CRS metadata.",
        )
    with col_up2:
        st.caption("Supported DEM Datasets:")
        st.markdown(
            "- NASA SRTM 30m / 90m\n"
            "- USGS 3DEP 10m / 1m\n"
            "- Copernicus GLO-30 DEM\n"
            "- Local projected / geographic GeoTIFF"
        )

    if dem_file:
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            inspect_btn = st.button("🔍 Inspect DEM Metadata", use_container_width=True)
        with col_btn2:
            process_btn = st.button("⚙️ Run Terrain Analysis (Slope & Aspect)", use_container_width=True)

        if inspect_btn:
            with st.spinner("Inspecting GeoTIFF header and CRS tags..."):
                dem_file.seek(0)
                files = {"file": (dem_file.name, dem_file.getvalue(), "image/tiff")}
                try:
                    resp = requests.post(f"{api_base_url}/api/v1/geospatial/dem/inspect", files=files, timeout=10.0)
                    if resp.status_code == 200:
                        st.session_state["dem_metadata"] = resp.json()
                        st.success("DEM metadata successfully inspected!")
                    else:
                        st.error(f"Inspection failed ({resp.status_code}): {resp.text}")
                except Exception as err:
                    st.error(f"Error communicating with backend: {err}")

        if process_btn:
            with st.spinner("Processing elevation, calculating slope gradients and aspect..."):
                dem_file.seek(0)
                files = {"file": (dem_file.name, dem_file.getvalue(), "image/tiff")}
                try:
                    resp = requests.post(f"{api_base_url}/api/v1/geospatial/dem/terrain", files=files, timeout=25.0)
                    if resp.status_code == 200:
                        terrain_data = resp.json()
                        st.session_state["terrain_results"] = terrain_data
                        st.session_state["dem_metadata"] = terrain_data.get("dem_metadata")
                        st.toast("Terrain analysis completed!", icon="✅")
                    else:
                        st.error(f"Terrain calculation failed ({resp.status_code}): {resp.text}")
                except Exception as err:
                    st.error(f"Error communicating with backend: {err}")

    # Display DEM Metadata if available
    dem_meta = st.session_state.get("dem_metadata")
    if dem_meta:
        with st.expander("📋 Inspected Raster Metadata & Georeferencing", expanded=True):
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Dimensions (W x H)", f"{dem_meta.get('width')} x {dem_meta.get('height')}")
            col_m2.metric("Pixel Resolution", f"{dem_meta.get('pixel_size_x', 0):.4f} units")
            col_m3.metric("CRS Type", "Geographic (Deg)" if dem_meta.get("is_geographic") else "Projected (Meters)")
            col_m4.metric("Valid Pixels", f"{dem_meta.get('valid_pixel_count', 0):,}")

            st.caption(f"**CRS Definition:** `{dem_meta.get('crs')}`")
            bounds = dem_meta.get("bounds", {})
            st.caption(
                f"**Bounding Coordinates:** West: `{bounds.get('minx'):.4f}`, "
                f"South: `{bounds.get('miny'):.4f}`, East: `{bounds.get('maxx'):.4f}`, North: `{bounds.get('maxy'):.4f}`"
            )
            if dem_meta.get("validation_messages"):
                for msg in dem_meta["validation_messages"]:
                    st.info(f"ℹ️ {msg}")

    # Display Terrain Results if available
    terrain_res = st.session_state.get("terrain_results")
    if terrain_res:
        st.divider()
        st.subheader("📊 Derived Terrain Metrics")
        elev = terrain_res.get("elevation", {})
        slope = terrain_res.get("slope", {})
        aspect = terrain_res.get("aspect", {})

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Elevation Range", f"{elev.get('min_elevation')}m - {elev.get('max_elevation')}m")
        c2.metric("Mean Elevation", f"{elev.get('mean_elevation')}m")
        c3.metric("Slope Range", f"{slope.get('min_slope_deg')}° - {slope.get('max_slope_deg')}°")
        c4.metric("Mean Slope", f"{slope.get('mean_slope_deg')}°")

        st.caption(
            f"**Aspect Convention:** {aspect.get('convention')}. "
            f"Flat terrain cells (<0.1° slope): `{aspect.get('flat_pixel_count', 0):,}` cells."
        )

        # Show Terrain Preview Image
        preview_id = terrain_res.get("preview_image_id")
        if preview_id:
            img_url = f"{api_base_url}/api/v1/geospatial/artifacts/{preview_id}"
            st.image(img_url, caption="Derived Terrain Analysis (Elevation, Slope, and Aspect)", use_container_width=True)

        # Download buttons for derived GeoTIFFs
        st.markdown("##### 📥 Download Processed Continuous GeoTIFF Rasters")
        cdl1, cdl2 = st.columns(2)
        slope_id = terrain_res.get("slope_raster_id")
        aspect_id = terrain_res.get("aspect_raster_id")

        if slope_id:
            with cdl1:
                try:
                    s_bytes = requests.get(f"{api_base_url}/api/v1/geospatial/artifacts/{slope_id}").content
                    st.download_button(
                        label="📄 Download Slope GeoTIFF (Degrees)",
                        data=s_bytes,
                        file_name="terrashield_slope_degrees.tif",
                        mime="image/tiff",
                        use_container_width=True,
                    )
                except Exception:
                    pass

        if aspect_id:
            with cdl2:
                try:
                    a_bytes = requests.get(f"{api_base_url}/api/v1/geospatial/artifacts/{aspect_id}").content
                    st.download_button(
                        label="📄 Download Aspect GeoTIFF (Azimuth)",
                        data=a_bytes,
                        file_name="terrashield_aspect_azimuth.tif",
                        mime="image/tiff",
                        use_container_width=True,
                    )
                except Exception:
                    pass


def render_ndvi_section(api_base_url: str) -> None:
    """Render the Sentinel-2 Red/NIR upload and NDVI processing UI."""
    st.markdown("### 🌿 Sentinel-2 NDVI (Vegetation Index) Engine")
    st.markdown(
        "Upload compatible Copernicus Sentinel-2 Red (Band 4) and Near-Infrared (Band 8) "
        "GeoTIFF rasters to compute the Normalized Difference Vegetation Index: "
        "$$\\text{NDVI} = \\frac{\\text{NIR} - \\text{Red}}{\\text{NIR} + \\text{Red}}$$"
    )

    cn1, cn2 = st.columns(2)
    with cn1:
        red_file = st.file_uploader("Upload Sentinel-2 Red Band (B04)", type=["tif", "tiff"], key="ndvi_red")
    with cn2:
        nir_file = st.file_uploader("Upload Sentinel-2 NIR Band (B08)", type=["tif", "tiff"], key="ndvi_nir")

    cloud_check = st.checkbox("Cloud mask applied in source acquisition product", value=False)

    if red_file and nir_file:
        if st.button("🚀 Calculate Sentinel-2 NDVI", use_container_width=True):
            with st.spinner("Aligning grids and computing NDVI array..."):
                red_file.seek(0)
                nir_file.seek(0)
                files = {
                    "red_file": (red_file.name, red_file.getvalue(), "image/tiff"),
                    "nir_file": (nir_file.name, nir_file.getvalue(), "image/tiff"),
                }
                data = {"cloud_masked": str(cloud_check)}
                try:
                    resp = requests.post(f"{api_base_url}/api/v1/geospatial/ndvi", files=files, data=data, timeout=25.0)
                    if resp.status_code == 200:
                        st.session_state["ndvi_results"] = resp.json()
                        st.toast("NDVI calculation completed!", icon="🌿")
                    else:
                        st.error(f"NDVI processing failed ({resp.status_code}): {resp.text}")
                except Exception as err:
                    st.error(f"Backend communication error: {err}")

    ndvi_data = st.session_state.get("ndvi_results")
    if ndvi_data:
        st.divider()
        st.subheader("📊 Processed NDVI Results")
        n_stats = ndvi_data.get("ndvi_stats", {})
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Min NDVI", f"{n_stats.get('min_ndvi', 0):.4f}")
        k2.metric("Max NDVI", f"{n_stats.get('max_ndvi', 0):.4f}")
        k3.metric("Mean NDVI", f"{n_stats.get('mean_ndvi', 0):.4f}")
        k4.metric("Valid Vegetation Cells", f"{n_stats.get('valid_pixels', 0):,}")

        if n_stats.get("zero_denominator_pixels", 0) > 0:
            st.caption(f"Zero denominator cells handled without error: `{n_stats.get('zero_denominator_pixels')}`")

        preview_id = ndvi_data.get("preview_image_id")
        if preview_id:
            st.image(f"{api_base_url}/api/v1/geospatial/artifacts/{preview_id}", caption="Processed NDVI Raster", use_container_width=True)

        raster_id = ndvi_data.get("ndvi_raster_id")
        if raster_id:
            try:
                r_bytes = requests.get(f"{api_base_url}/api/v1/geospatial/artifacts/{raster_id}").content
                st.download_button(
                    label="📄 Download Processed NDVI GeoTIFF",
                    data=r_bytes,
                    file_name="terrashield_ndvi.tif",
                    mime="image/tiff",
                    use_container_width=True,
                )
            except Exception:
                pass


def render_soil_and_vector_section(api_base_url: str) -> None:
    """Render the Soil Data Validation and Protected-Area Spatial Exclusion UI."""
    st.markdown("### 🛡️ Environmental Constraints: Protected Areas & Soil Data")

    tab_pa, tab_soil = st.tabs(["🌳 Protected-Area Boundaries & Exclusions", "🌱 SoilGrids Data Ingestion"])

    with tab_pa:
        st.markdown(
            "Upload a protected area vector file (GeoJSON) to evaluate spatial intersections "
            "against candidate parcels. Intersecting parcels are recommended for exclusion with explicit legal justification."
        )

        pa_file = st.file_uploader("Upload Protected Area Boundaries (GeoJSON)", type=["geojson", "json"], key="pa_uploader")
        if pa_file:
            if st.button("🔍 Evaluate Candidate Parcel Intersections", use_container_width=True):
                with st.spinner("Performing spatial intersections with candidate parcels..."):
                    pa_file.seek(0)
                    files = {"file": (pa_file.name, pa_file.getvalue(), "application/json")}
                    try:
                        resp = requests.post(f"{api_base_url}/api/v1/geospatial/vectors/intersections", files=files, timeout=15.0)
                        if resp.status_code == 200:
                            st.session_state["pa_results"] = resp.json()
                            st.toast("Spatial intersection evaluation complete!", icon="✅")
                        else:
                            st.error(f"Intersection evaluation failed: {resp.text}")
                    except Exception as err:
                        st.error(f"Error communicating with backend: {err}")

        pa_res = st.session_state.get("pa_results")
        if pa_res:
            st.divider()
            st.subheader("Spatial Exclusion Evaluation Results")
            st.metric("Total Parcels Evaluated", pa_res.get("total_parcels_evaluated"))
            st.metric("Parcels Intersecting Protected Areas", pa_res.get("intersecting_parcels_count"))

            results_list = pa_res.get("results", [])
            df_pa = pd.DataFrame(
                [
                    {
                        "Parcel ID": r.get("parcel_id"),
                        "Name": r.get("name"),
                        "Intersects Reserve": "Yes (Excluded)" if r.get("intersects_protected_area") else "No (Eligible)",
                        "Reserve Names": ", ".join(r.get("protected_area_names", [])) or "None",
                        "Overlap (ha)": r.get("overlap_area_hectares") or 0.0,
                        "Reason": r.get("reason") or "Clear of protected-area constraints",
                    }
                    for r in results_list
                ]
            )
            st.dataframe(df_pa, use_container_width=True, hide_index=True)

    with tab_soil:
        st.markdown("Validate soil dataset metadata against official ISRIC SoilGrids 250m specifications.")

        c_s1, c_s2 = st.columns(2)
        with c_s1:
            source = st.text_input("Data Source", value="ISRIC SoilGrids 250m")
            prop = st.selectbox(
                "Soil Property",
                options=["clay", "silt", "sand", "bdod (Bulk Density)", "soc (Organic Carbon)", "phh2o (pH)", "cfvo (Coarse Fragments)", "soil_depth"],
                index=0,
            )
        with c_s2:
            depth = st.selectbox("Depth Interval", options=["0-5cm", "5-15cm", "15-30cm", "30-60cm", "0-30cm", "60-100cm"], index=4)
            unit_val = st.text_input("Units", value="g/kg")

        if st.button("🧪 Validate Soil Metadata", use_container_width=True):
            clean_prop = prop.split()[0]
            payload = {
                "source": source,
                "property_name": clean_prop,
                "depth_interval": depth,
                "units": unit_val,
                "download_date": "2026-10-11",
            }
            try:
                resp = requests.post(f"{api_base_url}/api/v1/geospatial/soil/validate", json=payload, timeout=8.0)
                if resp.status_code == 200:
                    s_res = resp.json()
                    if s_res.get("is_valid"):
                        st.success(f"Soil metadata validated for '{clean_prop}' ({depth})!")
                    else:
                        st.warning("Validation messages:")
                        for msg in s_res.get("messages", []):
                            st.write(f"- {msg}")
                    st.info(f"**Notice:** {s_res.get('warning')}")
            except Exception as err:
                st.error(f"Error communicating with backend: {err}")
