"""Terrain analysis module: Elevation statistics, Slope (degrees), and Aspect (azimuth)."""

import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple
import matplotlib
matplotlib.use("Agg")  # Headless backend
import matplotlib.pyplot as plt
import numpy as np

from backend.app.core.config import settings
from backend.app.core.geospatial.coordinate_systems import get_meters_per_degree
from backend.app.core.geospatial.raster_loader import inspect_geotiff, write_geotiff
from backend.app.schemas.geospatial import (
    AspectStats,
    ElevationStats,
    RasterMetadata,
    SlopeStats,
    TerrainResponse,
)


def compute_elevation_stats(
    dem_array: np.ndarray, nodata_val: Optional[float] = None
) -> Tuple[ElevationStats, np.ndarray]:
    """Compute summary statistics for elevation and return a boolean valid-pixel mask."""
    float_dem = dem_array.astype(np.float64)
    if nodata_val is not None:
        if np.isnan(nodata_val):
            valid_mask = ~np.isnan(float_dem)
        else:
            valid_mask = ~np.isclose(float_dem, float(nodata_val)) & ~np.isnan(float_dem)
    else:
        valid_mask = ~np.isnan(float_dem)

    valid_pixels = float_dem[valid_mask]

    if valid_pixels.size == 0:
        return (
            ElevationStats(
                min_elevation=0.0,
                max_elevation=0.0,
                mean_elevation=0.0,
                median_elevation=0.0,
                unit="meters",
                valid_pixels=0,
                nodata_pixels=int(dem_array.size),
            ),
            valid_mask,
        )

    min_elev = float(np.min(valid_pixels))
    max_elev = float(np.max(valid_pixels))
    mean_elev = float(np.mean(valid_pixels))
    median_elev = float(np.median(valid_pixels))

    stats = ElevationStats(
        min_elevation=round(min_elev, 2),
        max_elevation=round(max_elev, 2),
        mean_elevation=round(mean_elev, 2),
        median_elevation=round(median_elev, 2),
        unit="meters",
        valid_pixels=int(valid_pixels.size),
        nodata_pixels=int(dem_array.size - valid_pixels.size),
    )
    return stats, valid_mask


def calculate_slope_and_aspect(
    dem_array: np.ndarray,
    metadata: RasterMetadata,
    valid_mask: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, SlopeStats, AspectStats]:
    """Calculate slope (in degrees) and aspect (in azimuth degrees from North).
    
    Gradient Calculation:
    - Central differences: dz/dx and dz/dy.
    - If CRS is geographic (degrees), horizontal step is scaled by meters_per_degree
      evaluated at the mean latitude of the raster bounds.
    - Slope: arctan(sqrt(dz_dx^2 + dz_dy^2)) * 180 / pi
    - Aspect: 90 - arctan2(dz_dy, -dz_dx) * 180 / pi, wrapped to [0, 360).
      Flat pixels (slope < 0.1°) are assigned -1.0° (flat).
    """
    rows, cols = dem_array.shape
    pixel_x = metadata.pixel_size_x
    pixel_y = metadata.pixel_size_y

    calculation_crs = "Projected (Meters)"
    center_lat = (metadata.bounds["miny"] + metadata.bounds["maxy"]) / 2.0
    if metadata.is_geographic and -90.0 <= center_lat <= 90.0:
        meters_x, meters_y = get_meters_per_degree(center_lat)
        dx_meters = pixel_x * meters_x
        dy_meters = pixel_y * meters_y
        calculation_crs = f"Geodesic Scaled (Latitude {center_lat:.3f}°: 1° lon={meters_x:.1f}m, 1° lat={meters_y:.1f}m)"
    else:
        dx_meters = pixel_x
        dy_meters = pixel_y

    # Protect against zero/invalid horizontal dimensions
    if dx_meters <= 0:
        dx_meters = 1.0
    if dy_meters <= 0:
        dy_meters = 1.0

    if rows < 2 or cols < 2:
        raise ValueError(f"Raster dimensions ({cols}x{rows}) are too small for 2D gradient slope analysis; minimum size is 2x2.")

    # Clean array for gradient calculation by filling nodata with local mean
    cleaned_dem = dem_array.astype(np.float64)
    mean_val = float(np.mean(cleaned_dem[valid_mask])) if np.any(valid_mask) else 0.0
    cleaned_dem[~valid_mask] = mean_val

    # 2D Central Differences
    # dy is along axis 0 (rows), dx is along axis 1 (cols)
    grad_y, grad_x = np.gradient(cleaned_dem, dy_meters, dx_meters)

    # In raster convention, row 0 is top (North) and rows increase southward
    # Therefore, dz_dy_north = -grad_y
    dz_dy_north = -grad_y
    dz_dx_east = grad_x

    # Slope in radians and degrees
    gradient_magnitude = np.sqrt(dz_dx_east**2 + dz_dy_north**2)
    slope_rad = np.arctan(gradient_magnitude)
    slope_deg = np.degrees(slope_rad)

    # Aspect in azimuth degrees from North (0°=N, 90°=E, 180°=S, 270°=W)
    # Using arctan2(east, north) gives direction of steepest descent
    aspect_rad = np.arctan2(-dz_dx_east, -dz_dy_north)
    aspect_deg = np.degrees(aspect_rad)
    # Convert from [-180, 180] to [0, 360)
    aspect_deg = np.where(aspect_deg < 0, aspect_deg + 360.0, aspect_deg)

    # Flag flat areas where slope is negligible (< 0.1 degrees)
    flat_mask = slope_deg < 0.1
    aspect_deg[flat_mask] = -1.0  # -1 denotes flat terrain

    # Apply nodata masking
    slope_deg[~valid_mask] = -9999.0
    aspect_deg[~valid_mask] = -9999.0

    # Statistics over valid pixels
    valid_slopes = slope_deg[valid_mask]
    if valid_slopes.size > 0:
        min_slope = float(np.min(valid_slopes))
        max_slope = float(np.max(valid_slopes))
        mean_slope = float(np.mean(valid_slopes))
    else:
        min_slope, max_slope, mean_slope = 0.0, 0.0, 0.0

    slope_stats = SlopeStats(
        min_slope_deg=round(min_slope, 2),
        max_slope_deg=round(max_slope, 2),
        mean_slope_deg=round(mean_slope, 2),
        method="2D Central Differences / Horn Formulation",
        calculation_crs=calculation_crs,
    )

    valid_aspects = aspect_deg[valid_mask & ~flat_mask]
    mean_aspect = float(np.mean(valid_aspects)) if valid_aspects.size > 0 else None

    aspect_stats = AspectStats(
        mean_aspect_deg=round(mean_aspect, 1) if mean_aspect is not None else None,
        flat_pixel_count=int(np.sum(flat_mask & valid_mask)),
    )

    return slope_deg, aspect_deg, slope_stats, aspect_stats


def generate_terrain_preview(
    dem: np.ndarray,
    slope: np.ndarray,
    aspect: np.ndarray,
    valid_mask: np.ndarray,
    output_png_path: Path,
) -> Path:
    """Generate a combined 3-panel terrain visualization preview PNG."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), dpi=120)

    # Elevation Panel
    dem_masked = np.ma.masked_array(dem, ~valid_mask)
    im0 = axes[0].imshow(dem_masked, cmap="terrain")
    axes[0].set_title("Elevation (m)")
    axes[0].axis("off")
    fig.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    # Slope Panel
    slope_masked = np.ma.masked_array(slope, ~valid_mask | (slope < 0))
    im1 = axes[1].imshow(slope_masked, cmap="viridis")
    axes[1].set_title("Slope (°)")
    axes[1].axis("off")
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    # Aspect Panel
    aspect_masked = np.ma.masked_array(aspect, ~valid_mask | (aspect < 0))
    im2 = axes[2].imshow(aspect_masked, cmap="twilight", vmin=0, vmax=360)
    axes[2].set_title("Aspect (Azimuth °)")
    axes[2].axis("off")
    fig.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    plt.tight_layout()
    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_png_path), bbox_inches="tight")
    plt.close(fig)
    return output_png_path


def process_dem_terrain(dem_path: Path) -> TerrainResponse:
    """Process a DEM GeoTIFF file: extract elevation stats, calculate slope & aspect,
    and persist derived GeoTIFFs and preview image.
    """
    dem_array, metadata = inspect_geotiff(dem_path)
    elev_stats, valid_mask = compute_elevation_stats(
        dem_array, nodata_val=metadata.nodata_value
    )

    slope_array, aspect_array, slope_stats, aspect_stats = calculate_slope_and_aspect(
        dem_array, metadata, valid_mask
    )

    run_id = uuid.uuid4().hex[:8]
    slope_filename = f"slope_{run_id}.tif"
    aspect_filename = f"aspect_{run_id}.tif"
    preview_filename = f"terrain_preview_{run_id}.png"

    slope_path = settings.ARTIFACTS_DIR / slope_filename
    aspect_path = settings.ARTIFACTS_DIR / aspect_filename
    preview_path = settings.ARTIFACTS_DIR / preview_filename

    write_geotiff(
        output_path=slope_path,
        array=slope_array,
        bounds=metadata.bounds,
        pixel_size_x=metadata.pixel_size_x,
        pixel_size_y=metadata.pixel_size_y,
        nodata_value=-9999.0,
        crs_str=metadata.crs or "WGS 84 / UTM zone 10N",
    )

    write_geotiff(
        output_path=aspect_path,
        array=aspect_array,
        bounds=metadata.bounds,
        pixel_size_x=metadata.pixel_size_x,
        pixel_size_y=metadata.pixel_size_y,
        nodata_value=-9999.0,
        crs_str=metadata.crs or "WGS 84 / UTM zone 10N",
    )

    generate_terrain_preview(
        dem=dem_array,
        slope=slope_array,
        aspect=aspect_array,
        valid_mask=valid_mask,
        output_png_path=preview_path,
    )

    notes = [
        "Slope calculated using documented 2D finite difference gradients.",
        "Aspect expressed as azimuth from North in degrees (0°-360°), with flat areas recorded as -1.0°.",
        "Slope steepness is an environmental terrain parameter, not a validated landslide probability.",
    ]
    if metadata.is_geographic:
        notes.append(
            "Geodesic scaling applied to convert geographic degree increments to metric dimensions."
        )

    return TerrainResponse(
        status="completed",
        dem_metadata=metadata,
        elevation=elev_stats,
        slope=slope_stats,
        aspect=aspect_stats,
        slope_raster_id=slope_filename,
        aspect_raster_id=aspect_filename,
        preview_image_id=preview_filename,
        notes=notes,
    )
