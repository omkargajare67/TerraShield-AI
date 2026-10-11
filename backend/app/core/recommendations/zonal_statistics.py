"""Raster-to-parcel zonal statistics aggregation across multi-resolution grids."""

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from backend.app.core.geospatial.raster_loader import inspect_geotiff


class RasterLayerContext:
    """In-memory wrapper for a single raster layer with spatial windowing helpers."""

    def __init__(self, file_path: Path, layer_name: str = ""):
        self.file_path = file_path
        self.layer_name = layer_name or file_path.stem
        self.exists = file_path.exists()
        self.data: Optional[np.ndarray] = None
        self.minx = 0.0
        self.miny = 0.0
        self.maxx = 0.0
        self.maxy = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.width = 0
        self.height = 0
        self.nodata: Optional[float] = -9999.0

        if self.exists:
            arr, meta = inspect_geotiff(file_path)
            self.data = arr
            self.minx = float(meta.bounds["minx"])
            self.miny = float(meta.bounds["miny"])
            self.maxx = float(meta.bounds["maxx"])
            self.maxy = float(meta.bounds["maxy"])
            self.width = meta.width
            self.height = meta.height
            self.dx = (self.maxx - self.minx) / float(self.width)
            self.dy = (self.maxy - self.miny) / float(self.height)
            self.nodata = meta.nodata_value if meta.nodata_value is not None else -9999.0

    def extract_parcel_window(
        self, p_minx: float, p_miny: float, p_maxx: float, p_maxy: float
    ) -> Optional[np.ndarray]:
        """Extract rectangular sub-window of raster data matching parcel bounding box."""
        if not self.exists or self.data is None:
            return None

        # Check for intersection with raster bounds
        if p_maxx <= self.minx or p_minx >= self.maxx or p_maxy <= self.miny or p_miny >= self.maxy:
            return None

        c0 = max(0, min(self.width - 1, int(math.floor((p_minx - self.minx) / self.dx))))
        c1 = max(c0 + 1, min(self.width, int(math.ceil((p_maxx - self.minx) / self.dx))))

        r0 = max(0, min(self.height - 1, int(math.floor((self.maxy - p_maxy) / self.dy))))
        r1 = max(r0 + 1, min(self.height, int(math.ceil((self.maxy - p_miny) / self.dy))))

        if r0 >= r1 or c0 >= c1:
            return None

        return self.data[r0:r1, c0:c1]


def extract_zonal_metrics_for_parcel(
    parcel_bounds: Tuple[float, float, float, float],
    dem_ctx: Optional[RasterLayerContext] = None,
    slope_ctx: Optional[RasterLayerContext] = None,
    aspect_ctx: Optional[RasterLayerContext] = None,
    fs_base_ctx: Optional[RasterLayerContext] = None,
    fs_reinf_ctx: Optional[RasterLayerContext] = None,
    fs_delta_ctx: Optional[RasterLayerContext] = None,
    req_cohesion_ctx: Optional[RasterLayerContext] = None,
    req_rar_ctx: Optional[RasterLayerContext] = None,
    req_density_ctx: Optional[RasterLayerContext] = None,
    ndvi_ctx: Optional[RasterLayerContext] = None,
    fs_target: float = 1.3,
) -> Dict[str, Any]:
    """Compute comprehensive zonal statistics for a single candidate parcel bounding box.

    Args:
        parcel_bounds: (min_lon, min_lat, max_lon, max_lat)
        dem_ctx: Elevation raster context (meters)
        slope_ctx: Slope raster context (degrees)
        aspect_ctx: Aspect raster context (azimuth degrees)
        fs_base_ctx: Baseline Factor of Safety raster context
        fs_reinf_ctx: Root-reinforced Factor of Safety raster context
        fs_delta_ctx: Modeled Factor of Safety increment (ΔFS) context
        req_cohesion_ctx: Required cohesion raster context (kPa)
        req_rar_ctx: Required RAR raster context
        req_density_ctx: Calibrated tree density raster context (stems/ha)
        ndvi_ctx: Sentinel-2 NDVI raster context
        fs_target: Benchmark Factor of Safety target (default 1.3)

    Returns:
        Dictionary of aggregated metrics and coverage statistics.
    """
    min_lon, min_lat, max_lon, max_lat = parcel_bounds
    metrics: Dict[str, Any] = {}

    # 0. DEM Elevation Metrics
    if dem_ctx and dem_ctx.exists:
        dem_win = dem_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if dem_win is not None and dem_win.size > 0:
            valid_mask = (dem_win != -9999.0) & ~np.isnan(dem_win)
            valid_vals = dem_win[valid_mask]
            if valid_vals.size > 0:
                metrics["elevation_mean_m"] = round(float(np.mean(valid_vals)), 1)
                metrics["elevation_min_m"] = round(float(np.min(valid_vals)), 1)
                metrics["elevation_max_m"] = round(float(np.max(valid_vals)), 1)
            else:
                metrics["elevation_mean_m"] = None
                metrics["elevation_min_m"] = None
                metrics["elevation_max_m"] = None
        else:
            metrics["elevation_mean_m"] = None
    else:
        metrics["elevation_mean_m"] = None

    # 1. Slope Metrics
    if slope_ctx and slope_ctx.exists:
        sl_win = slope_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if sl_win is not None and sl_win.size > 0:
            valid_mask = (sl_win != -9999.0) & ~np.isnan(sl_win) & (sl_win >= 0.0)
            valid_vals = sl_win[valid_mask]
            total_px = sl_win.size
            valid_px = int(np.sum(valid_mask))
            metrics["terrain_coverage_pct"] = round(100.0 * valid_px / max(1, total_px), 2)
            metrics["terrain_valid_pixel_count"] = valid_px

            if valid_px > 0:
                metrics["slope_mean_deg"] = round(float(np.mean(valid_vals)), 2)
                metrics["slope_median_deg"] = round(float(np.median(valid_vals)), 2)
                metrics["slope_max_deg"] = round(float(np.max(valid_vals)), 2)
                metrics["slope_min_deg"] = round(float(np.min(valid_vals)), 2)
                # Fraction of steep cells (> 25 deg)
                metrics["fraction_steep_slope"] = round(float(np.sum(valid_vals > 25.0) / valid_px), 4)
            else:
                metrics["slope_mean_deg"] = None
                metrics["slope_median_deg"] = None
                metrics["slope_max_deg"] = None
                metrics["fraction_steep_slope"] = None
        else:
            metrics["terrain_coverage_pct"] = 0.0
            metrics["terrain_valid_pixel_count"] = 0
            metrics["slope_mean_deg"] = None
    else:
        metrics["terrain_coverage_pct"] = None
        metrics["terrain_valid_pixel_count"] = 0
        metrics["slope_mean_deg"] = None

    # 2. Aspect Metrics
    if aspect_ctx and aspect_ctx.exists:
        asp_win = aspect_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if asp_win is not None and asp_win.size > 0:
            valid_mask = (asp_win >= 0.0) & ~np.isnan(asp_win)  # -1 is flat, -9999 is nodata
            valid_vals = asp_win[valid_mask]
            if valid_vals.size > 0:
                metrics["aspect_mean_deg"] = round(float(np.mean(valid_vals)), 1)
            else:
                metrics["aspect_mean_deg"] = None
        else:
            metrics["aspect_mean_deg"] = None
    else:
        metrics["aspect_mean_deg"] = None

    # 3. Geotechnical Stability Metrics (Phase 3 inputs)
    if fs_base_ctx and fs_base_ctx.exists:
        fb_win = fs_base_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if fb_win is not None and fb_win.size > 0:
            valid_mask = (fb_win > 0.0) & (fb_win != -9999.0) & ~np.isnan(fb_win)
            valid_vals = fb_win[valid_mask]
            if valid_vals.size > 0:
                metrics["fs_baseline_mean"] = round(float(np.mean(valid_vals)), 3)
                metrics["fs_baseline_median"] = round(float(np.median(valid_vals)), 3)
                metrics["fs_baseline_min"] = round(float(np.min(valid_vals)), 3)
                # Fraction of cells failing target benchmark
                sub_count = int(np.sum(valid_vals < fs_target))
                metrics["fraction_subtarget_fs"] = round(float(sub_count / len(valid_vals)), 4)
                # Fraction unstable (< 1.0)
                unstable_count = int(np.sum(valid_vals < 1.0))
                metrics["fraction_unstable_fs"] = round(float(unstable_count / len(valid_vals)), 4)
            else:
                metrics["fs_baseline_mean"] = None
                metrics["fs_baseline_median"] = None
                metrics["fraction_subtarget_fs"] = 0.0
                metrics["fraction_unstable_fs"] = 0.0
        else:
            metrics["fs_baseline_mean"] = None
    else:
        metrics["fs_baseline_mean"] = None

    # Reinforced FS
    if fs_reinf_ctx and fs_reinf_ctx.exists:
        fr_win = fs_reinf_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if fr_win is not None and fr_win.size > 0:
            valid_mask = (fr_win > 0.0) & (fr_win != -9999.0) & ~np.isnan(fr_win)
            valid_vals = fr_win[valid_mask]
            metrics["fs_reinforced_mean"] = round(float(np.mean(valid_vals)), 3) if valid_vals.size > 0 else None
            metrics["fs_reinforced_median"] = round(float(np.median(valid_vals)), 3) if valid_vals.size > 0 else None
        else:
            metrics["fs_reinforced_mean"] = None
    else:
        metrics["fs_reinforced_mean"] = None

    # Delta FS
    if fs_delta_ctx and fs_delta_ctx.exists:
        fd_win = fs_delta_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if fd_win is not None and fd_win.size > 0:
            valid_mask = (fd_win != -9999.0) & ~np.isnan(fd_win)
            valid_vals = fd_win[valid_mask]
            metrics["fs_delta_mean"] = round(float(np.mean(valid_vals)), 3) if valid_vals.size > 0 else None
            metrics["fs_delta_max"] = round(float(np.max(valid_vals)), 3) if valid_vals.size > 0 else None
        else:
            metrics["fs_delta_mean"] = None
    else:
        metrics["fs_delta_mean"] = None

    # Required Cohesion (kPa)
    if req_cohesion_ctx and req_cohesion_ctx.exists:
        rc_win = req_cohesion_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if rc_win is not None and rc_win.size > 0:
            valid_mask = (rc_win >= 0.0) & (rc_win != -9999.0) & ~np.isnan(rc_win)
            valid_vals = rc_win[valid_mask]
            metrics["req_cohesion_mean_kpa"] = round(float(np.mean(valid_vals)), 3) if valid_vals.size > 0 else None
        else:
            metrics["req_cohesion_mean_kpa"] = None
    else:
        metrics["req_cohesion_mean_kpa"] = None

    # Required RAR
    if req_rar_ctx and req_rar_ctx.exists:
        rr_win = req_rar_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if rr_win is not None and rr_win.size > 0:
            valid_mask = (rr_win >= 0.0) & (rr_win != -9999.0) & ~np.isnan(rr_win)
            valid_vals = rr_win[valid_mask]
            metrics["req_rar_mean"] = round(float(np.mean(valid_vals)), 6) if valid_vals.size > 0 else None
        else:
            metrics["req_rar_mean"] = None
    else:
        metrics["req_rar_mean"] = None

    # Required Tree Density (stems/ha)
    if req_density_ctx and req_density_ctx.exists:
        rd_win = req_density_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if rd_win is not None and rd_win.size > 0:
            valid_mask = (rd_win >= 0.0) & (rd_win != -9999.0) & ~np.isnan(rd_win)
            valid_vals = rd_win[valid_mask]
            metrics["req_density_mean_stems_ha"] = round(float(np.mean(valid_vals)), 1) if valid_vals.size > 0 else None
        else:
            metrics["req_density_mean_stems_ha"] = None
    else:
        metrics["req_density_mean_stems_ha"] = None

    # 4. Sentinel-2 NDVI Metrics (Finer 10m grid, 1099x1099)
    if ndvi_ctx and ndvi_ctx.exists:
        nd_win = ndvi_ctx.extract_parcel_window(min_lon, min_lat, max_lon, max_lat)
        if nd_win is not None and nd_win.size > 0:
            valid_mask = (nd_win != -9999.0) & ~np.isnan(nd_win) & (nd_win >= -1.0) & (nd_win <= 1.0)
            valid_vals = nd_win[valid_mask]
            total_px = nd_win.size
            valid_px = int(np.sum(valid_mask))
            metrics["ndvi_coverage_pct"] = round(100.0 * valid_px / max(1, total_px), 2)
            metrics["ndvi_valid_pixel_count"] = valid_px

            if valid_px > 0:
                metrics["ndvi_mean"] = round(float(np.mean(valid_vals)), 4)
                metrics["ndvi_median"] = round(float(np.median(valid_vals)), 4)
                metrics["ndvi_min"] = round(float(np.min(valid_vals)), 4)
                metrics["ndvi_max"] = round(float(np.max(valid_vals)), 4)
                # Fraction of dense canopy proxy (NDVI > 0.60)
                metrics["fraction_dense_canopy_proxy"] = round(float(np.sum(valid_vals > 0.60) / valid_px), 4)
            else:
                metrics["ndvi_mean"] = None
                metrics["ndvi_median"] = None
                metrics["fraction_dense_canopy_proxy"] = 0.0
        else:
            metrics["ndvi_coverage_pct"] = 0.0
            metrics["ndvi_mean"] = None
            metrics["fraction_dense_canopy_proxy"] = 0.0
    else:
        metrics["ndvi_coverage_pct"] = None
        metrics["ndvi_mean"] = None
        metrics["fraction_dense_canopy_proxy"] = 0.0

    # Ensure standardized alias keys across modules
    metrics["required_cohesion_mean_kpa"] = metrics.get("req_cohesion_mean_kpa")
    metrics["tree_density_mean_stems_ha"] = metrics.get("req_density_mean_stems_ha")

    return metrics


def extract_parcel_zonal_statistics(
    parcel_poly: Any,
    bounds: Tuple[float, float, float, float],
    slope_ctx: Optional[RasterLayerContext] = None,
    dem_ctx: Optional[RasterLayerContext] = None,
    aspect_ctx: Optional[RasterLayerContext] = None,
    ndvi_ctx: Optional[RasterLayerContext] = None,
    fs_base_ctx: Optional[RasterLayerContext] = None,
    fs_reinf_ctx: Optional[RasterLayerContext] = None,
    fs_delta_ctx: Optional[RasterLayerContext] = None,
    req_c_ctx: Optional[RasterLayerContext] = None,
    tree_d_ctx: Optional[RasterLayerContext] = None,
    fs_target: float = 1.3,
    ndvi_canopy_threshold: float = 0.65,
) -> Dict[str, Any]:
    """Convenience wrapper extracting all zonal metrics for a candidate parcel."""
    return extract_zonal_metrics_for_parcel(
        parcel_bounds=bounds,
        dem_ctx=dem_ctx,
        slope_ctx=slope_ctx,
        aspect_ctx=aspect_ctx,
        fs_base_ctx=fs_base_ctx,
        fs_reinf_ctx=fs_reinf_ctx,
        fs_delta_ctx=fs_delta_ctx,
        req_cohesion_ctx=req_c_ctx,
        req_density_ctx=tree_d_ctx,
        ndvi_ctx=ndvi_ctx,
        fs_target=fs_target,
    )
