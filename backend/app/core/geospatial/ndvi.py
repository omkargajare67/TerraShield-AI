"""Sentinel-2 Normalized Difference Vegetation Index (NDVI) processing module."""

import uuid
from pathlib import Path
from typing import Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from backend.app.core.config import settings
from backend.app.core.geospatial.raster_loader import inspect_geotiff, write_geotiff
from backend.app.schemas.geospatial import NDVIResponse, NDVIStats


def calculate_ndvi_array(
    red_array: np.ndarray,
    nir_array: np.ndarray,
    red_nodata: float | None = None,
    nir_nodata: float | None = None,
) -> Tuple[np.ndarray, NDVIStats]:
    """Calculate NDVI = (NIR - Red) / (NIR + Red) with robust zero-denominator handling."""
    if red_array.shape != nir_array.shape:
        raise ValueError(
            f"Band dimension mismatch: Red is {red_array.shape}, but NIR is {nir_array.shape}."
        )

    # Cast to float32
    red = red_array.astype(np.float32)
    nir = nir_array.astype(np.float32)

    # Valid mask
    valid_mask = ~np.isnan(red) & ~np.isnan(nir)
    if red_nodata is not None and not np.isnan(red_nodata):
        valid_mask &= ~np.isclose(red, red_nodata)
    if nir_nodata is not None and not np.isnan(nir_nodata):
        valid_mask &= ~np.isclose(nir, nir_nodata)

    numerator = nir - red
    denominator = nir + red

    zero_denom_mask = np.isclose(denominator, 0.0) | (denominator < 0)
    zero_denom_count = int(np.sum(zero_denom_mask & valid_mask))

    # Mask valid calculation cells
    calc_mask = valid_mask & ~zero_denom_mask

    ndvi = np.full_like(red, -9999.0, dtype=np.float32)
    ndvi[calc_mask] = numerator[calc_mask] / denominator[calc_mask]

    # Clip mathematically valid range [-1.0, 1.0] with tolerance
    ndvi[calc_mask] = np.clip(ndvi[calc_mask], -1.0, 1.0)

    valid_cells = ndvi[calc_mask]
    if valid_cells.size > 0:
        min_v = float(np.min(valid_cells))
        max_v = float(np.max(valid_cells))
        mean_v = float(np.mean(valid_cells))
    else:
        min_v, max_v, mean_v = 0.0, 0.0, 0.0

    stats = NDVIStats(
        min_ndvi=round(min_v, 4),
        max_ndvi=round(max_v, 4),
        mean_ndvi=round(mean_v, 4),
        valid_pixels=int(valid_cells.size),
        zero_denominator_pixels=zero_denom_count,
    )

    return ndvi, stats


def generate_ndvi_preview(
    ndvi: np.ndarray, output_png_path: Path
) -> Path:
    """Generate a clean single-panel preview PNG of NDVI with RdYlGn colormap."""
    fig, ax = plt.subplots(figsize=(7, 6), dpi=120)
    ndvi_masked = np.ma.masked_array(ndvi, ndvi < -1.0)

    im = ax.imshow(ndvi_masked, cmap="RdYlGn", vmin=-0.2, vmax=0.9)
    ax.set_title("Sentinel-2 Normalized Difference Vegetation Index (NDVI)")
    ax.axis("off")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="NDVI Index")

    plt.tight_layout()
    output_png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_png_path), bbox_inches="tight")
    plt.close(fig)
    return output_png_path


def process_sentinel2_ndvi(
    red_path: Path, nir_path: Path, cloud_masked: bool = False
) -> NDVIResponse:
    """Execute complete NDVI pipeline across input Sentinel-2 Red and NIR band files."""
    red_arr, red_meta = inspect_geotiff(red_path)
    nir_arr, nir_meta = inspect_geotiff(nir_path)

    if red_arr.shape != nir_arr.shape:
        raise ValueError(
            f"Input bands must have identical pixel dimensions. "
            f"Red band: {red_arr.shape}, NIR band: {nir_arr.shape}."
        )

    ndvi_arr, stats = calculate_ndvi_array(
        red_arr, nir_arr, red_meta.nodata_value, nir_meta.nodata_value
    )

    run_id = uuid.uuid4().hex[:8]
    ndvi_filename = f"ndvi_{run_id}.tif"
    preview_filename = f"ndvi_preview_{run_id}.png"

    ndvi_path = settings.ARTIFACTS_DIR / ndvi_filename
    preview_path = settings.ARTIFACTS_DIR / preview_filename

    write_geotiff(
        output_path=ndvi_path,
        array=ndvi_arr,
        bounds=red_meta.bounds,
        pixel_size_x=red_meta.pixel_size_x,
        pixel_size_y=red_meta.pixel_size_y,
        nodata_value=-9999.0,
        crs_str=red_meta.crs or "WGS 84 / UTM zone 10N",
    )

    generate_ndvi_preview(ndvi_arr, preview_path)

    provenance = (
        f"Computed via Sentinel-2 Red band ({red_path.name}) and NIR band ({nir_path.name}). "
        f"NDVI = (NIR - Red) / (NIR + Red)."
    )
    warning = (
        "NDVI reflects relative surface greenness and vegetative vigor. "
        "It is not a direct measurement of tree species composition, root cohesion, "
        "or slope stability."
    )
    if not cloud_masked:
        warning += " No atmospheric/cloud mask was applied; cloud shadows may distort index values."

    return NDVIResponse(
        status="completed",
        ndvi_stats=stats,
        ndvi_raster_id=ndvi_filename,
        preview_image_id=preview_filename,
        provenance=provenance,
        warning=warning,
    )
